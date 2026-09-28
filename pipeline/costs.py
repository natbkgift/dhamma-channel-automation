"""DhammaLab cost attribution (THB). Every direct-API call writes a ledger line with model, token usage,
category and experiment (env DHAMMALAB_EXP). Prices are THB per token, calibrated from the Cloud Billing
SKU report for Sep 2026 (usage cost / usage, before savings) -> re-calibrate monthly from Billing.

python3 costs.py                 -> cost by category and by experiment from the ledger
python3 costs.py --exp EXP-10    -> one experiment
"""
import os, sys, json, collections
LEDGER = os.path.expanduser('~/.config/dhammalab/tts_ledger.jsonl')
# THB per output token (Billing SKU usage cost / usage count, 1-28 Sep 2026)
PRICE_OUT = {
    'gemini-3.8-flash-tts': 360.92 / 609458,          # audio out (Billing then applied -50% "other savings")
    'gemini-3.5-transcribe': 0.0,                      # billed on audio INPUT, see PRICE_IN
    'gemini-3.8-flash': 22.68 / 183815,
    'gemini-3-pro-image-preview': 244.77 / 62000, 'gemini-3-pro-image': 244.77 / 62000,
    'gemini-omni-1.1-flash': 1033.75 / 1795520,
}
PRICE_PER_CALL = {'lyria-3.5': 0.08 * 33, 'lyria-3-pro-preview': 0.08 * 33, 'lyria-3-clip-preview': 0.04 * 33}  # USD/song * ~33 THB; RealTime price not published
PRICE_IN = {'gemini-3.5-transcribe': 24.22 / 368163}
CATEGORY = {'tts': 'TTS', 'transcription_qa': 'Transcription / QA', 'image': 'Image generation',
            'video': 'Video / motion', 'music': 'Music generation'}

def cost(e):
    u = e.get('usage') or {}; m = e.get('model', '')
    out = u.get('candidatesTokenCount') or u.get('total_output_tokens') or 0
    inp = u.get('promptTokenCount') or u.get('total_input_tokens') or 0
    if m in PRICE_PER_CALL: return PRICE_PER_CALL[m]
    return out * PRICE_OUT.get(m, 0) + inp * PRICE_IN.get(m, 0)

def load(exp=None):
    rows = []
    if os.path.exists(LEDGER):
        for line in open(LEDGER):
            try: e = json.loads(line)
            except ValueError: continue
            if not e.get('ok'): continue
            if exp and e.get('exp') != exp: continue
            rows.append(e)
    return rows

def report(exp=None):
    by_cat = collections.defaultdict(float); by_exp = collections.defaultdict(float); n = collections.Counter()
    for e in load(exp):
        c = cost(e); cat = CATEGORY.get(e.get('category', 'tts'), 'Other')
        by_cat[cat] += c; by_exp[e.get('exp', 'unassigned')] += c; n[cat] += 1
    return {'by_category_thb': {k: round(v, 2) for k, v in by_cat.items()}, 'calls': dict(n),
            'by_experiment_thb': {k: round(v, 2) for k, v in by_exp.items()}}

if __name__ == '__main__':
    exp = sys.argv[sys.argv.index('--exp') + 1] if '--exp' in sys.argv else None
    print(json.dumps(report(exp), ensure_ascii=False, indent=1))
