"""python -m dataanalyzer.analyze 진입점

사용법:
    python -m dataanalyzer.analyze \\
        --target_dir train_data \\
        --output_dir train_data \\
        --model_name Qwen/Qwen2.5-7B-Instruct
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib import font_manager

# 한글 폰트 설정 (Noto Sans CJK KR)
_KO_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(_KO_FONT_PATH).exists():
    font_manager.fontManager.addfont(_KO_FONT_PATH)
    _ko_prop = font_manager.FontProperties(fname=_KO_FONT_PATH)
    plt.rcParams["font.family"] = _ko_prop.get_name()
plt.rcParams["axes.unicode_minus"] = False

try:
    from transformers import AutoTokenizer
    _TOKENIZER_AVAILABLE = True
except ImportError:
    _TOKENIZER_AVAILABLE = False

# datagen.config에서 tools 명세 가져오기
sys.path.insert(0, str(Path(__file__).parent.parent))
from datagen.config import tools as TOOLS_SPEC


# ── 파싱 유틸 ──────────────────────────────────────────────────────────────

_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_TOOL_RESPONSE_RE = re.compile(r"<tool_response>\s*(.*?)\s*</tool_response>", re.DOTALL)


def load_records(target_dir: Path) -> list[dict]:
    """target_dir 내 모든 *.jsonl 레코드를 로드한다.
    messages 키가 없는 레코드(배치 입력 등)는 건너뛴다.
    """
    records = []
    for path in sorted(target_dir.glob("*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    if "messages" in rec:
                        records.append(rec)
    return records


def _parse_tool_call(content: str) -> dict | None:
    m = _TOOL_CALL_RE.search(content)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _parse_tool_response_raw(content: str) -> str | None:
    m = _TOOL_RESPONSE_RE.search(content)
    return m.group(1) if m else None


# ── optional 파라미터 추출 ──────────────────────────────────────────────────

def _get_optional_params() -> dict[str, list[str]]:
    """함수명 → optional 파라미터 이름 리스트 반환."""
    result = {}
    for tool in TOOLS_SPEC:
        name = tool["name"]
        params = tool.get("parameters", {})
        all_props = list(params.get("properties", {}).keys())
        required = params.get("required", [])
        result[name] = [p for p in all_props if p not in required]
    return result


# ── 분석 함수들 ─────────────────────────────────────────────────────────────

def analyze_tool_distribution(records: list[dict]) -> dict[str, int]:
    """함수별 총 호출 횟수."""
    counts: dict[str, int] = defaultdict(int)
    for rec in records:
        for msg in rec["messages"]:
            if msg["role"] == "assistant":
                tc = _parse_tool_call(msg["content"])
                if tc:
                    counts[tc.get("name", "unknown")] += 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def analyze_sequential_calls(records: list[dict]) -> list[int]:
    """대화당 (tool_call→tool_response) 연속 쌍의 최대 체인 길이."""
    result = []
    for rec in records:
        messages = rec["messages"]
        max_chain = 0
        current_chain = 0
        i = 0
        while i < len(messages):
            msg = messages[i]
            if (msg["role"] == "assistant"
                    and _parse_tool_call(msg["content"])
                    and i + 1 < len(messages)
                    and _TOOL_RESPONSE_RE.search(messages[i + 1]["content"])):
                current_chain += 1
                max_chain = max(max_chain, current_chain)
                i += 2
            else:
                current_chain = 0
                i += 1
        result.append(max_chain)
    return result


def analyze_turn_counts(records: list[dict]) -> list[int]:
    """대화당 turn 수 (user 일반 발화 수 기준).
    tool_response를 포함한 user 메시지는 turn으로 집계하지 않는다.
    """
    result = []
    for rec in records:
        count = sum(
            1
            for m in rec["messages"]
            if m["role"] == "user" and not _TOOL_RESPONSE_RE.search(m["content"])
        )
        result.append(count)
    return result


def analyze_total_tokens(records: list[dict], tokenizer) -> list[int]:
    """대화당 전체 토큰 수 (system_prompt + messages 합산)."""
    result = []
    for rec in records:
        parts = []
        if rec.get("system_prompt"):
            parts.append(rec["system_prompt"])
        parts.extend(m["content"] for m in rec["messages"])
        text = " ".join(parts)
        result.append(len(tokenizer.encode(text, add_special_tokens=False)))
    return result


def analyze_param_coverage(records: list[dict]) -> tuple[dict, dict]:
    """함수별 optional 파라미터 사용률과 unique value 비율.

    Returns:
        usage_rate:   {func: {param: float 0~1}}
        unique_ratio: {func: {param: float 0~1}}
    """
    optional_params = _get_optional_params()
    call_counts: dict[str, int] = defaultdict(int)
    param_uses: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    param_values: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))

    for rec in records:
        for msg in rec["messages"]:
            if msg["role"] == "assistant":
                tc = _parse_tool_call(msg["content"])
                if tc:
                    name = tc.get("name", "")
                    args = tc.get("arguments", {})
                    call_counts[name] += 1
                    for param in optional_params.get(name, []):
                        if param in args:
                            param_uses[name][param] += 1
                            param_values[name][param].add(
                                json.dumps(args[param], ensure_ascii=False, sort_keys=True)
                            )

    usage_rate: dict[str, dict[str, float]] = {}
    unique_ratio: dict[str, dict[str, float]] = {}
    for func, opts in optional_params.items():
        if not opts or call_counts[func] == 0:
            continue
        usage_rate[func] = {}
        unique_ratio[func] = {}
        for param in opts:
            uses = param_uses[func][param]
            usage_rate[func][param] = uses / call_counts[func]
            unique_ratio[func][param] = (
                len(param_values[func][param]) / uses if uses > 0 else 0.0
            )

    return usage_rate, unique_ratio


def analyze_token_by_role(records: list[dict], tokenizer) -> dict[str, list[int]]:
    """user 일반발화 / assistant 일반발화 / tool_call / tool_response 별 토큰 수 분포."""
    buckets: dict[str, list[int]] = {
        "user_plain": [],
        "assistant_plain": [],
        "tool_call": [],
        "tool_response": [],
    }
    for rec in records:
        for msg in rec["messages"]:
            content = msg["content"]
            n = len(tokenizer.encode(content, add_special_tokens=False))
            if msg["role"] == "assistant":
                if _TOOL_CALL_RE.search(content):
                    buckets["tool_call"].append(n)
                else:
                    buckets["assistant_plain"].append(n)
            elif msg["role"] == "user":
                if _TOOL_RESPONSE_RE.search(content):
                    buckets["tool_response"].append(n)
                else:
                    buckets["user_plain"].append(n)
    return buckets


def analyze_tool_response_size(records: list[dict], tokenizer) -> dict[str, list[int]]:
    """함수별 tool_response 토큰 수 분포."""
    sizes: dict[str, list[int]] = defaultdict(list)
    for rec in records:
        messages = rec["messages"]
        last_func: str | None = None
        for msg in messages:
            if msg["role"] == "assistant":
                tc = _parse_tool_call(msg["content"])
                if tc:
                    last_func = tc.get("name")
            elif msg["role"] == "user":
                raw = _parse_tool_response_raw(msg["content"])
                if raw and last_func:
                    n = len(tokenizer.encode(raw, add_special_tokens=False))
                    sizes[last_func].append(n)
                    last_func = None
    return dict(sizes)


# ── 플롯 함수들 ─────────────────────────────────────────────────────────────

def _save_bar(data: dict[str, int], title: str, xlabel: str, path: Path) -> None:
    keys = list(data.keys())
    vals = list(data.values())
    fig, ax = plt.subplots(figsize=(max(8, len(keys) * 0.9), 5))
    bars = ax.bar(range(len(keys)), vals)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys, rotation=45, ha="right", fontsize=9)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("count")
    for bar, val in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.2,
            str(val),
            ha="center", va="bottom", fontsize=8,
        )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


def _save_hist(
    values: list[int],
    title: str,
    xlabel: str,
    path: Path,
    bins: int = 15,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(values, bins=bins, edgecolor="black", alpha=0.8)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("conversations")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    if values:
        mean_val = sum(values) / len(values)
        ax.axvline(mean_val, color="red", linestyle="--", label=f"mean={mean_val:.1f}")
        ax.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


def _save_int_bar(
    values: list[int],
    title: str,
    xlabel: str,
    path: Path,
) -> None:
    """정수 데이터 전용 bar chart. 각 정수값이 독립 막대로 표시된다."""
    from collections import Counter
    counts = Counter(values)
    xs = list(range(min(counts), max(counts) + 1))
    ys = [counts.get(x, 0) for x in xs]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(xs, ys, edgecolor="black", alpha=0.8)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("conversations")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    if values:
        mean_val = sum(values) / len(values)
        ax.axvline(mean_val, color="red", linestyle="--", label=f"mean={mean_val:.1f}")
        ax.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


def _save_bar_role(buckets: dict[str, list[int]], path: Path) -> None:
    labels = list(buckets.keys())
    means = [sum(v) / len(v) if v else 0.0 for v in buckets.values()]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, means)
    ax.set_title("role별 평균 토큰 수")
    ax.set_xlabel("role")
    ax.set_ylabel("avg tokens")
    for bar, val in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{val:.1f}",
            ha="center", va="bottom", fontsize=9,
        )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


def _save_boxplot(
    data: dict[str, list[int]],
    title: str,
    ylabel: str,
    path: Path,
) -> None:
    labels = list(data.keys())
    values = [data[k] for k in labels]
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.2), 5))
    ax.boxplot(values, tick_labels=labels, showfliers=True)
    ax.set_title(title)
    ax.set_xlabel("function")
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


# ── 텍스트 리포트 ────────────────────────────────────────────────────────────

def write_param_coverage_txt(
    usage_rate: dict,
    unique_ratio: dict,
    path: Path,
) -> None:
    lines = ["# 파라미터 커버리지 분석", ""]
    for func in sorted(usage_rate):
        lines.append(f"## {func}")
        for param in sorted(usage_rate[func]):
            ur = usage_rate[func][param] * 100
            uniq = unique_ratio[func].get(param, 0.0) * 100
            lines.append(
                f"  {param:<25s}  사용률: {ur:5.1f}%  unique값 비율: {uniq:5.1f}%"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary_txt(
    n_records: int,
    token_counts: list[int],
    path: Path,
) -> None:
    total = sum(token_counts)
    mean = total / len(token_counts) if token_counts else 0.0
    lines = [
        "# 데이터셋 요약",
        f"대화 수          : {n_records:,}",
        f"총 토큰 수       : {total:,}",
        f"대화당 평균 토큰 : {mean:.1f}",
        f"대화당 최소 토큰 : {min(token_counts) if token_counts else 0:,}",
        f"대화당 최대 토큰 : {max(token_counts) if token_counts else 0:,}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="학습 데이터셋 분포 분석")
    parser.add_argument("--target_dir", required=True, help="*.jsonl이 위치한 디렉토리")
    parser.add_argument("--output_dir", required=True, help="결과 저장 디렉토리")
    parser.add_argument("--model_name", required=True, help="토크나이저 모델 이름")
    args = parser.parse_args()

    target = Path(args.target_dir)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # 1. 데이터 로드
    print(f"[1/8] JSONL 로드: {target}")
    records = load_records(target)
    if not records:
        print(f"[오류] {target} 에 *.jsonl 파일이 없습니다.")
        raise SystemExit(1)
    print(f"       {len(records)}개 대화 로드 완료")

    # 2. 토크나이저 로드
    print(f"[2/8] 토크나이저 로드: {args.model_name}")
    if not _TOKENIZER_AVAILABLE:
        print("[오류] transformers 패키지가 필요합니다.")
        raise SystemExit(1)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    # 3. tool 분포
    print("[3/8] tool 분포 분석...")
    tool_dist = analyze_tool_distribution(records)
    _save_bar(tool_dist, "Tool 호출 분포", "함수명", output / "tool_distribution.png")

    # 4. sequential call
    print("[4/8] sequential call 분포 분석...")
    seq_calls = analyze_sequential_calls(records)
    _save_int_bar(
        seq_calls,
        "Sequential Call 수 분포",
        "최대 연속 tool_call 체인 길이",
        output / "sequential_calls.png",
    )

    # 5. turn 수
    print("[5/8] turn 수 분포 분석...")
    turns = analyze_turn_counts(records)
    _save_int_bar(turns, "대화 Turn 수 분포", "turn 수", output / "turn_count.png")

    # 6. 토큰 수
    print("[6/8] 토큰 수 분포 분석...")
    token_counts = analyze_total_tokens(records, tokenizer)
    _save_hist(token_counts, "대화당 총 토큰 수 분포", "토큰 수", output / "total_tokens.png")
    write_summary_txt(len(records), token_counts, output / "summary.txt")

    # 7. 파라미터 커버리지
    print("[7/8] 파라미터 커버리지 분석...")
    usage_rate, unique_ratio = analyze_param_coverage(records)
    write_param_coverage_txt(usage_rate, unique_ratio, output / "param_coverage.txt")

    # 8. 토큰 길이 세분화
    print("[8/8] 토큰 길이 세분화 분석...")
    role_tokens = analyze_token_by_role(records, tokenizer)
    _save_bar_role(role_tokens, output / "token_by_role.png")
    resp_sizes = analyze_tool_response_size(records, tokenizer)
    if resp_sizes:
        _save_boxplot(
            resp_sizes,
            "Tool Response 크기 분포 (함수별)",
            "토큰 수",
            output / "tool_response_size.png",
        )

    total_tokens = sum(token_counts)
    print(f"\n[완료] 결과 저장: {output.resolve()}")
    print(f"  총 토큰 수: {total_tokens:,}")
    print(f"  생성된 파일 수: {len(list(output.iterdir()))}개")


if __name__ == "__main__":
    main()
