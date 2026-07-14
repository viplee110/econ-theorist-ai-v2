# V5 pilot preflight manifest

Captured: 2026-07-14, before the first `etai` invocation  
Clean root: `C:\tmp\etai-v5-public-pilot-20260714`  
Python: `3.12.10`  
Environment construction: `venv --system-site-packages`, followed by offline
wheel installation with `--no-index --no-deps`

## Frozen source and distribution

- source commit: `de9de84db486975ffc63d2e51adcd1ca8dbd3a05`
- distribution: `econ_theorist_ai-0.1.0-py3-none-any.whl`
- wheel bytes: `647318`
- wheel SHA-256:
  `8CA2E91911EA8A42C956B6FF4C12595C81C13A932D964855FCD9996D888E0004`
- offline build backend: `setuptools 83.0.0`, `wheel 0.47.0`

## Clean-root inventory before first invocation

The only top-level entries were:

- `.agents/`
- `.host-localappdata/` (empty isolated operational-home parent)
- `.venv/`
- `CASE.md`
- `distribution/`

The virtual environment contained 1,152 files totaling 17,721,133 bytes. Its
scientific/runtime inputs outside `.venv` were exactly:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `.agents/skills/econ-theorist-v2/agents/openai.yaml` | 296 | `D0DB034C3C93616CB42390DF90343F13A45F81AF6CBE48D4B678FC54E0E09C17` |
| `.agents/skills/econ-theorist-v2/SKILL.md` | 3,976 | `4238AA882B5A82E38B979EBC6B0787A4EBBA6DA2673DBA132CDC3292898665F4` |
| `CASE.md` | 2,797 | `9B67D683141675F794292A6CF3F046E624E469F17860E0253F6185CD3C864FF2` |
| `distribution/econ_theorist_ai-0.1.0-py3-none-any.whl` | 647,318 | `8CA2E91911EA8A42C956B6FF4C12595C81C13A932D964855FCD9996D888E0004` |

No source checkout, test, fixture, gold case, prior output, audit, reference
candidate, or literature file was copied into the clean root.

The `Research seed` block in `generator_case.md` is byte-for-byte identical to
the corresponding block in the preserved pre-V5 `case.md`: 1,237 UTF-8 bytes,
SHA-256
`7EBD071530BD591D7B689A5946132AAF2007F817632A65FC1CC8F3A2F46CD2CB`.
Only the execution horizon changed—from the old first-route-only pilot to the
V5 pre-G1 route sequence required by this protocol.

## Installed package snapshot

The engine's pinned runtime dependencies were:

- `econ-theorist-ai==0.1.0`
- `pydantic==2.13.4`
- `pydantic_core==2.46.4`
- `annotated-types==0.7.0`
- `typing_extensions==4.15.0`
- `typing-inspection==0.4.2`

The environment inherited additional packages from the read-only verification
Python through `--system-site-packages`. They are not engine dependencies and
were not supplied as scientific context. The complete inherited package list
at preflight was:

```text
absl-py==2.4.0
annotated-doc==0.0.4
anyio==4.13.0
certifi==2026.5.20
cffi==2.0.0
charset-normalizer==3.4.7
click==8.4.1
colorama==0.4.6
contourpy==1.3.3
cryptography==49.0.0
cycler==0.12.1
decorator==5.3.1
fastapi==0.136.3
flatbuffers==25.12.19
fonttools==4.63.0
h11==0.16.0
httpcore2==2.5.0
httptools==0.8.0
httpx2==2.5.0
idna==3.18
ImageIO==2.37.3
imageio-ffmpeg==0.6.0
kiwisolver==1.5.0
matplotlib==3.10.9
mediapipe==0.10.35
moviepy==2.2.1
mpmath==1.3.0
numpy==2.4.4
opencv-contrib-python==4.13.0.92
opencv-python==4.13.0.92
packaging==26.2
pandas==3.0.2
pdfminer.six==20260107
pdfplumber==0.11.10
pillow==12.2.0
pip==25.0.1
proglog==0.1.12
pycparser==3.0
pymupdf==1.28.0
pyparsing==3.3.2
pypdf==6.12.0
pypdfium2==5.11.0
python-dateutil==2.9.0.post0
python-dotenv==1.2.2
python-multipart==0.0.32
PyYAML==6.0.3
scipy==1.17.1
six==1.17.0
sounddevice==0.5.5
starlette==1.3.1
sympy==1.14.0
tqdm==4.68.2
truststore==0.10.4
tzdata==2026.2
uvicorn==0.49.0
watchfiles==1.2.0
websockets==16.0
yt-dlp==2026.6.9
z3-solver==4.16.0.0
```
