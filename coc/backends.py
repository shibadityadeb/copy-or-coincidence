"""Model backends. Each takes a batch of chat requests (each with its own seed) and returns text.

mlx  : Apple-silicon Mac, quantised weights; for development slices only.
vllm : Kaggle 2x T4, fp16; for every reported number.
fake : deterministic stub for tests.
Never mix backends or quantisations for the same agent inside one experiment (guide §9).
"""
import hashlib
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Request:
    system: str
    user: str
    seed: int
    temperature: float
    top_p: float
    max_tokens: int
    enable_thinking: bool = False
    json_schema: Optional[dict] = None     # if set, decoding is constrained to valid JSON of this shape
    prompt_format: str = "chat"            # "chat" = model's chat template; "plain" = text prompt (base models)


@dataclass
class Generation:
    text: str
    prompt_tokens: int
    output_tokens: int
    truncated: bool
    latency_ms: float


class Backend:
    name = "base"
    framework_version = ""
    quantization = ""
    dtype = ""

    def generate(self, reqs: list[Request]) -> list[Generation]:
        raise NotImplementedError


# The reply shape from prompts/solver_v1.txt. maxItems caps runaway step lists.
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "final": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["steps", "final", "confidence"],
    "additionalProperties": False,
}


# Plain-text prompt for models without a chat template (OLMo-3 base): same instructions and question.
PLAIN_PROMPT = "{system}\n\nProblem:\n{user}\n\nResponse:\n"
# Few-shot variant (one documented fix after the base-model pilot truncated 6.1% of answers): two neutral
# worked examples showing the concise format. Deliberately no trick question and no "unanswerable" case.
PLAIN_FEWSHOT_PROMPT = (
    "{system}\n\n"
    "Problem:\nA box holds 12 pencils. How many pencils are in 5 boxes?\n\n"
    'Response:\n{{"steps": ["Each box holds 12 pencils.", "5 boxes hold 5 * 12 = 60 pencils."], "final": "60", "confidence": 0.95}}\n\n'
    "Problem:\nEvery rose is a flower. Every flower is a plant. Mia's gift is a rose.\n"
    "Is the following statement true or false? Mia's gift is a plant.\n\n"
    'Response:\n{{"steps": ["Mia\'s gift is a rose.", "Every rose is a flower, and every flower is a plant.", '
    '"So Mia\'s gift is a plant."], "final": "true", "confidence": 0.95}}\n\n'
    "Problem:\n{user}\n\nResponse:\n")


def _messages(r: Request) -> list[dict]:
    return [{"role": "system", "content": r.system}, {"role": "user", "content": r.user}]


class FakeBackend(Backend):
    """Answers are a deterministic function of (seed, question): lets tests check plumbing and resume."""
    name, framework_version, quantization, dtype = "fake", "0", "none", "none"

    def __init__(self, answers: Optional[dict[str, list[str]]] = None):
        self.answers = answers or {}
        self.calls = 0

    def generate(self, reqs):
        out = []
        for r in reqs:
            self.calls += 1
            opts = self.answers.get(r.user, ["42", "7", "unanswerable"])
            pick = opts[int(hashlib.sha256(str(r.seed).encode()).hexdigest(), 16) % len(opts)]
            text = '{"steps": ["fake"], "final": "%s", "confidence": 0.5}' % pick
            out.append(Generation(text, len(r.user.split()), 12, False, 0.0))
        return out


class MLXBackend(Backend):
    """No constrained decoding here: json_schema is ignored, so Mac parse rates are a lower bound."""
    name = "mlx"

    def __init__(self, repo: str, revision: str, quantization: str):
        import mlx.core as mx
        import mlx_lm
        from mlx_lm import load

        self.mx, self.mlx_lm = mx, mlx_lm
        self.model, self.tok = load(repo, revision=revision)
        self.framework_version = f"mlx-lm {mlx_lm.__version__}; mlx {mx.__version__}"
        self.quantization, self.dtype = quantization, "mlx"

    def generate(self, reqs):
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        out = []
        for r in reqs:                       # one at a time: seeds stay per-trial, no batch effects
            prompt = self.tok.apply_chat_template(_messages(r), add_generation_prompt=True, tokenize=False,
                                                  enable_thinking=r.enable_thinking)
            n_prompt = len(self.tok.encode(prompt))
            self.mx.random.seed(r.seed)
            t0 = time.perf_counter()
            text = generate(self.model, self.tok, prompt, max_tokens=r.max_tokens,
                            sampler=make_sampler(temp=r.temperature, top_p=r.top_p), verbose=False)
            n_out = len(self.tok.encode(text))
            out.append(Generation(text, n_prompt, n_out, n_out >= r.max_tokens,
                                  (time.perf_counter() - t0) * 1000))
        return out


class VLLMBackend(Backend):
    """Any extra key in an agent config's "vllm" block is passed to vllm.LLM unchanged
    (e.g. "attention_backend": "FLEX_ATTENTION")."""
    name = "vllm"

    def __init__(self, repo: str, revision: str, dtype: str = "float16", tensor_parallel_size: int = 1,
                 max_model_len: int = 4096, gpu_memory_utilization: float = 0.90, max_num_seqs: int = 128,
                 enable_prefix_caching: bool = False, limit_mm_per_prompt: Optional[dict] = None,
                 patch_config: Optional[dict] = None, **engine_kwargs):
        import vllm
        from vllm import LLM

        if patch_config:
            # Load from a local snapshot whose config.json has these keys replaced (weights untouched).
            # Used for OLMo-3 RL-Zero, whose config names its architecture "olmo2-retrofit".
            import json as _json
            from huggingface_hub import snapshot_download
            local = snapshot_download(repo, revision=revision, local_dir=f"/tmp/patched-{repo.replace('/', '--')}")
            cfg_path = f"{local}/config.json"
            cfg = _json.load(open(cfg_path))
            cfg.update(patch_config)
            _json.dump(cfg, open(cfg_path, "w"), indent=2)
            repo, revision = local, None
        mm = {"image": 0, "video": 0} if limit_mm_per_prompt is None else limit_mm_per_prompt
        self.llm = LLM(model=repo, revision=revision, dtype=dtype, tensor_parallel_size=tensor_parallel_size,
                       max_model_len=max_model_len, gpu_memory_utilization=gpu_memory_utilization,
                       max_num_seqs=max_num_seqs, enable_prefix_caching=enable_prefix_caching, seed=0,
                       **({"limit_mm_per_prompt": mm} if mm else {}), **engine_kwargs)
        self.tok = self.llm.get_tokenizer()
        self.framework_version = f"vllm {vllm.__version__}"
        self.quantization, self.dtype = "none", dtype

    def generate(self, reqs):
        from vllm import SamplingParams

        def constraint(schema):
            if schema is None:
                return {}
            try:                                    # vLLM >= 0.10.2
                from vllm.sampling_params import StructuredOutputsParams
                return {"structured_outputs": StructuredOutputsParams(json=schema)}
            except ImportError:                     # older vLLM
                from vllm.sampling_params import GuidedDecodingParams
                return {"guided_decoding": GuidedDecodingParams(json=schema)}

        prompts = [PLAIN_PROMPT.format(system=r.system, user=r.user) if r.prompt_format == "plain" else
                   PLAIN_FEWSHOT_PROMPT.format(system=r.system, user=r.user) if r.prompt_format == "plain_fewshot" else
                   self.tok.apply_chat_template(_messages(r), add_generation_prompt=True, tokenize=False,
                                                enable_thinking=r.enable_thinking) for r in reqs]
        params = [SamplingParams(temperature=r.temperature, top_p=r.top_p, max_tokens=r.max_tokens,
                                 seed=r.seed, **constraint(r.json_schema)) for r in reqs]
        t0 = time.perf_counter()
        res = self.llm.generate(prompts, params, use_tqdm=False)
        per = (time.perf_counter() - t0) * 1000 / max(len(reqs), 1)   # batch wall time, amortised
        out = []
        for r, o in zip(reqs, res):
            c = o.outputs[0]
            out.append(Generation(c.text, len(o.prompt_token_ids), len(c.token_ids),
                                  c.finish_reason == "length", per))
        return out
