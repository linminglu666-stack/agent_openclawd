import os
import re
import glob
from collections import defaultdict, Counter

SOURCE_DIR = "/home/maco_six/.openclaw/workspace/memory/training"
OUTPUT_DIR = "/home/maco_six/.openclaw/workspace/MD2/training_summaries_v7"
GROUP_SIZE = 10

def clean_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r"[()（）\[\]【】]", "", name)
    name = re.sub(r"[：:]", "", name)
    name = re.sub(r"[—–-]+", "_", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

def looks_like_code(line):
    if line.startswith("```"):
        return True
    if line.count("|") >= 2:
        return True
    code_tokens = ["def ", "class ", "return ", "import ", "public ", "private ", "async ", "await ", "=>", "{", "}", ";"]
    return any(token in line for token in code_tokens)

def normalize_bullet(line):
    line = re.sub(r"^[-*•]\s*", "", line)
    line = re.sub(r"^\d+[.)]\s*", "", line)
    return line.strip()

def extract_info_from_file(filepath):
    title = ""
    points = []
    insights = []
    in_suggestion = False
    in_insight = False
    in_code = False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return "", [], []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not title and line.startswith("# "):
            raw_title = line[2:]
            raw_title = re.sub(r"P\d+_R\d+[:\s]*", "", raw_title)
            title = raw_title.strip()
            continue
        if re.match(r"#+\s", line):
            in_suggestion = bool(re.search(r"(建议|优化|方案|落地|实践|行动|strategy|action|suggestion)", line, re.IGNORECASE))
            in_insight = bool(re.search(r"(洞察|启示|关键点|核心观点|insight)", line, re.IGNORECASE))
            continue
        if line.startswith(">") or looks_like_code(line):
            continue
        if line.startswith(("-", "*", "•")) or re.match(r"^\d+[.)]\s", line):
            item = normalize_bullet(line)
            if in_insight:
                insights.append(item)
            elif in_suggestion:
                points.append(item)
    return title, points, insights

def extract_keywords(text):
    chinese = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    english = re.findall(r"[A-Za-z]{2,}", text)
    stop_cn = {"训练", "深度", "理解", "报告", "系统", "架构", "方案", "优化", "分析", "设计", "计划", "轮次", "总结", "记录", "文档", "核心", "主题", "使用", "策略", "结果", "阶段", "问题", "解决", "洞察", "启示", "实践", "目标", "现状", "对于", "例如", "因此", "所以", "虽然", "而是", "我们", "他们", "这种", "那些", "以及"}
    stop_en = {"training", "plan", "round", "report", "system", "architecture", "analysis", "the", "and", "for", "with", "from", "into", "that"}
    allow_en = {"api", "chrome", "flask", "cron", "dag", "finops", "cache", "search", "model", "routing", "token", "graph", "tenant", "cost", "latency", "error", "trace"}
    bad_cn_substrings = ["训练", "深度理解", "报告", "记录", "总结", "结果", "阶段", "问题", "解决", "方案", "优化", "实践", "目标", "现状", "核心", "主题", "对于", "例如", "因此", "所以", "虽然", "而是", "我们", "他们", "这种", "那些", "以及", "月份", "个月"]
    chinese = [w for w in chinese if w not in stop_cn and not any(b in w for b in bad_cn_substrings)]
    english = [w.lower() for w in english if w.lower() not in stop_en and w.lower() in allow_en]
    counts = Counter(chinese + english)
    keywords = [w for w, _ in counts.most_common(6)]
    return keywords

def has_chinese(word):
    return re.search(r"[\u4e00-\u9fff]", word) is not None

def normalize_title(title):
    title = re.sub(r"(深度理解训练报告|深度理解训练记录|深度理解训练笔记|深度理解训练|训练报告|训练记录|训练笔记|报告|记录|总结|方案|分析|深度理解)", "", title)
    title = re.sub(r"Plan\s*\d+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"Round\s*\d+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"Training\s*Session", "", title, flags=re.IGNORECASE)
    title = re.sub(r"Deep\s*Training", "", title, flags=re.IGNORECASE)
    title = title.strip(" :-—_")
    return title

def is_meaningful_title(title):
    if not title:
        return False
    if len(title) < 4:
        return False
    if re.search(r"(训练|报告|记录|总结)$", title):
        return False
    if re.search(r"(Plan|Round|Training)", title, re.IGNORECASE):
        return False
    if title.strip().lower() in {"analysis", "overview", "summary"}:
        return False
    return True

def generate_actionable_plan(text):
    rules = [
        (["记忆", "memory", "context", "上下文"], "分层记忆与上下文压缩：短期上下文摘要化、长期记忆索引化，提供可回滚的记忆巩固流程"),
        (["检索", "搜索", "routing", "路由"], "多引擎路由与成本感知：按查询意图选择引擎，加入成本上限与质量回退策略"),
        (["缓存", "cache"], "分层缓存体系：L1本地缓存+L2共享缓存+失效广播，避免热点击穿"),
        (["延迟", "latency", "超时"], "性能与超时控制：设定分层超时与尾部延迟保护，支持部分结果快速返回"),
        (["错误", "error", "可靠性", "熔断"], "可靠性防护：熔断、退避重试、故障隔离与降级策略联动"),
        (["日志", "观测", "trace", "可视化"], "可观测性增强：统一埋点规范，链路追踪聚合到控制台可视化"),
        (["质量", "评估", "评价", "metric"], "质量评估闭环：定义离线评测集与线上指标，建立策略灰度与对照实验"),
        (["多租户", "配额", "成本"], "多租户与配额治理：配额池+租户限流，支持优先级与账单可追溯"),
        (["安全", "权限", "合规"], "安全与权限模型：细粒度权限、审计日志与数据脱敏策略")
    ]
    text_lower = text.lower()
    plan = []
    for keys, action in rules:
        if any(k.lower() in text_lower for k in keys):
            plan.append(action)
    defaults = [
        "核心流程标准化：输入规范化、意图识别、工具选择、结果合成形成可复用流水线",
        "数据与配置热更新：配置变更可追踪、可回滚，控制台实时生效",
        "异常样本回流：失败与低质量样本进入专项训练与修复队列"
    ]
    for item in defaults:
        if item not in plan:
            plan.append(item)
    return plan[:10]

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    files_map = defaultdict(list)
    all_files = glob.glob(os.path.join(SOURCE_DIR, "P*_R*.md"))
    for fp in all_files:
        filename = os.path.basename(fp)
        match = re.match(r"^P(\d+)_R(\d+)\.md$", filename)
        if match:
            p_num = int(match.group(1))
            r_num = int(match.group(2))
            files_map[p_num].append((r_num, fp))
    for p_num in sorted(files_map.keys()):
        entries = sorted(files_map[p_num], key=lambda x: x[0])
        for i in range(0, len(entries), GROUP_SIZE):
            range_entries = entries[i:i + GROUP_SIZE]
            if not range_entries:
                continue
            batch_titles = []
            batch_points = []
            batch_insights = []
            for r, fp in range_entries:
                title, points, insights = extract_info_from_file(fp)
                if title:
                    batch_titles.append(title)
                batch_points.extend(points)
                batch_insights.extend(insights)
            min_r = range_entries[0][0]
            max_r = range_entries[-1][0]
            range_label = f"R{min_r:02d}-{max_r:02d}"
            keywords = extract_keywords(" ".join(batch_titles + batch_points + batch_insights))
            cn_keywords = [k for k in keywords if has_chinese(k)]
            en_keywords = [k for k in keywords if not has_chinese(k)]
            clean_title = normalize_title(batch_titles[0]) if batch_titles else ""
            if is_meaningful_title(clean_title):
                summary_name = clean_title
            elif cn_keywords:
                summary_name = "与".join(cn_keywords[:2]) + "优化"
            elif en_keywords:
                summary_name = "_".join(en_keywords[:2]) + "_优化"
            else:
                summary_name = "架构优化"
            summary_name = clean_filename(summary_name)[:24] or "架构优化"
            plan_items = generate_actionable_plan(" ".join(keywords + batch_points + batch_insights))
            md_content = []
            md_content.append(f"# {summary_name} (P{p_num:03d} {range_label})")
            md_content.append("")
            md_content.append("## 1. 分组范围")
            md_content.append(f"- 覆盖文件数: {len(range_entries)}")
            md_content.append(f"- R编号范围: {range_label}")
            if batch_titles:
                md_content.append(f"- 代表主题: {batch_titles[0]}")
            if keywords:
                md_content.append(f"- 关键词: {', '.join(keywords[:5])}")
            md_content.append("")
            md_content.append("## 2. 关键洞察")
            if batch_insights:
                for item in list(dict.fromkeys(batch_insights))[:8]:
                    md_content.append(f"- {item}")
            else:
                md_content.append("- 未显式标注洞察，已由优化方案覆盖")
            md_content.append("")
            md_content.append("## 3. 可落地优化方案")
            for item in plan_items:
                md_content.append(f"- {item}")
            out_filename = f"P{p_num:03d}_{summary_name}_{range_label}.md"
            out_path = os.path.join(OUTPUT_DIR, out_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_content))
            print(f"Generated: {out_filename}")

if __name__ == "__main__":
    main()
