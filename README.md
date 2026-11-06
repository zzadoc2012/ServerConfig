# ServerConfig

피닉스다트 사내 어드민에 머신 컨피그를 적용하는 운영툴입니다.

## 실행 (개발)

```
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

1. `⚙️ SET`에서 Test Admin / Live Admin ID·PW를 저장합니다. 비밀번호는 Windows DPAPI로 암호화되어 `%APPDATA%\ServerConfig\credentials.dat`에 저장됩니다.
2. MACHINE, 컨피그, 브라우저, 운영 환경을 고른 뒤 `실행`을 누릅니다.

엑셀 원본은 `data/config.xlsx`입니다. exe와 같은 폴더의 `data\config.xlsx`가 있으면 그 파일을 우선합니다.

## exe 빌드

```
.\.venv\Scripts\pyinstaller --noconfirm --distpath dist\ServerConfig ServerConfig.spec
.\.venv\Scripts\python tools\sync_dist_data.py
```

결과 파일: `dist\ServerConfig\ServerConfig.exe`  
데이터: `dist\ServerConfig\data\` (exe와 같은 폴더의 `data\config.xlsx`를 읽고 추가 저장합니다)

## 주의

- 로그인 폼 식별자(`admin_id`, `passwd`, `login_btn`)는 테스트 어드민 페이지에서 확인했습니다.
- 로그인 이후 Machine / Mac Addr / Search / Config / EDIT 화면은 계정 없이 DOM을 확인하지 못했습니다. 해당 단계는 후보 로케이터로 탐색하며, 실패하면 로그에 남깁니다.
- 규격서에 MAC이 없는 머신은 실행이 막힙니다. `data/machines.json`을 보완하세요.
- 라이브 환경은 실행 전 확인 창이 뜹니다.
