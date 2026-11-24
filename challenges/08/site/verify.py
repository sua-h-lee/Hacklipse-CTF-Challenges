#!/usr/bin/env python3
"""출제 전 자동 검증. 사용법:  python3 -I verify.py"""
import os, re, struct, subprocess, sys, zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, *a)

STRICT_FLAG = os.environ["CTF_FLAG_08"]
if not re.fullmatch(r"HKL\{[^{}\r\n]+\}", STRICT_FLAG):
    raise ValueError("CTF_FLAG_08 must have the form HKL{...}")
if STRICT_FLAG != "HKL{" + "비스타블루베이커리카페" + "}":
    raise ValueError("CTF_FLAG_08 must encode the cafe name used by this challenge")
LENIENT = [
    r"(?i)^HKL\{\s*비스타[\s_-]*블루([\s_-]*베이커리)?([\s_-]*카페)?\s*\}$",
    r"(?i)^HKL\{\s*vista[\s_-]*blue([\s_-]*bakery)?([\s_-]*cafe)?\s*\}$",
]
# 배포물 어디에도 있으면 안 되는 문자열 (정답 유출)
LEAK = ["비스타", "vista", "blue", "snipaste", "screenshot", "solution", "hkl{"]

ACCEPT = [  # 관대 채점 시 정답 처리되어야 하는 입력
    "HKL{비스타블루베이커리카페}",
    "HKL{비스타블루 베이커리카페}",
    "HKL{비스타블루 베이커리 카페}",
    "HKL{비스타 블루 베이커리 카페}",
    "HKL{비스타블루베이커리}",
    "HKL{비스타블루}",
    "HKL{Vista Blue}",
    "HKL{vista_blue_cafe}",
    "HKL{VistaBlue Bakery Cafe}",
]
REJECT = [  # 오답으로 걸러져야 하는 입력
    "HKL{비스타블루호텔}",
    "HKL{바다정원}",
    "HKL{비스타블루베이커리카페페}",
    "flag{비스타블루베이커리카페}",
    "비스타블루베이커리카페",
    "HKL{}",
    "HKL{블루비스타}",
]

ok = True
def chk(cond, label, detail=""):
    global ok
    ok &= bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))

print("\n[1] 배포 파일 존재 / 비배포 파일 격리")
chk(os.path.exists(P("dist", "cafe.png")), "dist/cafe.png 존재")
chk(os.path.exists(P("salty-air.zip")), "salty-air.zip 존재")
chk(os.path.exists(P("src")), "src/ 원본 보관됨 (배포 금지 디렉터리)")

print("\n[2] zip 내용물 — 참가자에게 갈 파일만 들어있는가")
with zipfile.ZipFile(P("salty-air.zip")) as z:
    names = z.namelist()
    chk(names == ["cafe.png"], "zip에 cafe.png 1개만 포함", f"실제: {names}")
    blob = z.read("cafe.png")
chk(blob == open(P("dist", "cafe.png"), "rb").read(), "zip 안의 PNG == dist/cafe.png")

print("\n[3] PNG 메타데이터 — 정답/출처 흔적 제거 확인")
i, chunks = 8, []
while i < len(blob):
    ln = struct.unpack(">I", blob[i:i+4])[0]
    t = blob[i+4:i+8].decode("latin1")
    chunks.append(t)
    i += 12 + ln
    if t == "IEND":
        break
textish = [c for c in chunks if c in ("tEXt", "iTXt", "zTXt", "eXIf", "tIME")]
chk(not textish, "텍스트/EXIF 청크 없음", f"청크: {sorted(set(chunks))}")

print("\n[4] 아카이브 바이트 전체 유출 문자열 스캔")
raw = open(P("salty-air.zip"), "rb").read()
for kw in LEAK:
    hit = kw.encode() in raw.lower() or kw.encode("utf-8") in raw
    chk(not hit, f"'{kw}' 미검출")

print("\n[5] 배포용 설명문에 정답 노출 없음")
desc = open(P("description.md"), encoding="utf-8").read()
chk("비스타" not in desc, "description.md에 상호명 없음")
chk("베이커리카페}" not in desc, "예시 형식이 실제 접미사를 흘리지 않음")

print("\n[6] challenge.yml 정합성")
try:
    import yaml
    config_path = os.getenv("CTF_CHALLENGE_YAML", P("challenge.yml"))
    y = yaml.safe_load(open(config_path, encoding="utf-8"))
    chk(STRICT_FLAG in y.get("flags", []), "yaml의 flag == 정답")
    for f in y.get("files", []):
        chk(os.path.exists(P(f)), f"files 항목 실재: {f}")
    chk("비스타" not in y.get("description", ""), "yaml description에 정답 없음")
except ImportError:
    chk(False, "PyYAML 설치 필요")

print("\n[7] 플래그 채점 로직 (관대 채점 정규식)")
def grade(s):
    return s == STRICT_FLAG or any(re.match(p, s) for p in LENIENT)
for s in ACCEPT:
    chk(grade(s), f"정답 처리: {s}")
for s in REJECT:
    chk(not grade(s), f"오답 처리: {s}")

print("\n" + ("=" * 46))
print("결과:", "전체 통과 ✅" if ok else "실패 항목 있음 ❌")
print("=" * 46)
print("\n※ 이 스크립트는 '패키지'만 검증한다. 문제가 실제로 풀리는지는")
print("   README.md의 '출제 전 체크리스트' — 리버스 이미지 서치 + 외부 테스터 —")
print("   를 반드시 사람이 직접 수행해야 한다.\n")
sys.exit(0 if ok else 1)
