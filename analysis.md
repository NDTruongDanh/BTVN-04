# Analysis — Tra cứu chính sách đúng phiên bản

## 0. Stage 00: giới hạn của agent

- `stage-00-chat/agent.py`: `TOOLS = []`.
- `stage-00-chat/prompts.py`: `CAPABILITY_PROMPT` ghi rõ không có tool, không đọc/ghi file, không chạy lệnh.
- Gửi trường hợp A mà không dán nội dung chính sách: agent không có `tool result` nào để căn cứ, chỉ trả lời từ kiến thức sẵn có. Theo `BASE_PROMPT` lẽ ra phải nói rõ giới hạn thay vì đoán, nhưng vẫn không thể cho số ngày, phí hay dẫn tài liệu vì không đọc được file.
- Kết luận: thiếu tool đọc/liệt kê tài liệu nên không kiểm chứng được phiên bản, ngày hay phí.

## 1. Tool `list_files` (stage 01 + stage 02)

Mã nguồn:

- `stage-01-files/tools/files.py`: `_list(workspace, path)` + `@tool list_files(path: str)`.
- `stage-02-skills/tools/files.py`: giống hệt stage 01.
- Đăng ký: `stage-01-files/tools/__init__.py`, `stage-02-skills/tools/__init__.py` export `list_files`; `stage-01-files/agent.py`, `stage-02-skills/agent.py`: `TOOLS = [read_file, write_file, list_files]`.
- Prompt: `prompts.py` `CAPABILITY_PROMPT` thêm một dòng generic về `list_files` (tìm rồi dùng `read_file` để đọc). Không ghi tên file, nội dung chính sách hay đáp án trong tool hay prompt. Đã kiểm tra `grep policy-before/policy-from` trong `tools/`, `prompts.py`, `agent.py` đều không có.

Hành vi:

- Chỉ liệt kê một cấp (`iterdir`, không đệ quy), mỗi mục `{name, path, type: file|directory}`, `path` tương đối workspace, sắp xếp theo `name`.
- Tái dùng `_resolve`/`_error` của tool file hiện có: chặn `..`, đường dẫn tuyệt đối, `~`, symlink dẫn ra ngoài (`PATH_OUTSIDE_WORKSPACE`).
- Không tồn tại → `FILE_NOT_FOUND`; là file → `NOT_A_DIRECTORY` (lỗi rõ ràng, không trả danh sách rỗng); liệt kê lỗi IO → `LIST_FAILED`.

Kiểm tra tool trực tiếp (dữ liệu giả, không đọc thông tin cá nhân):

| Đầu vào | Kết quả | Bằng chứng |
|---|---|---|
| `data/policies` (hợp lệ) | `ok=true`, 2 entries `policy-before-oct.md`, `policy-from-oct.md` | `test_list_ok_sorted_and_single_level`, `test_list_tool_registered_and_returns_json` |
| `data/weekly_notes.md` (là file) | `ok=false`, `NOT_A_DIRECTORY` | `test_list_errors_for_file_missing_and_outside` |
| `data/khong-ton-tai` (không tồn tại) | `ok=false`, `FILE_NOT_FOUND` | cùng test trên |
| `../secret.txt`, `data/../../secret.txt`, đường dẫn tuyệt đối, `data/link.txt` symlink ra ngoài | `ok=false`, `PATH_OUTSIDE_WORKSPACE` | `test_list_errors...`, `test_list_symlink_escape_blocked` |

Chạy offline (mock model, không cần API key):

- `uv run pytest` trong `stage-01-files`: **38 passed**.
- `uv run pytest` trong `stage-02-skills`: **45 passed**.
- Các test mới: `test_list_ok_sorted_and_single_level`, `test_list_errors_for_file_missing_and_outside`, `test_list_symlink_escape_blocked`, `test_list_tool_registered_and_returns_json` ở cả hai stage.
- Test đăng ký đã cập nhật: `test_registered_tools` expects `["read_file","write_file","list_files"]`, `test_app.py` expects `Tools được cấp (3)`, stage 02 expects `Skills trong catalog (2)`.

## 2. Dữ liệu chính sách

Tạo ở cả hai stage, cả `fixtures/` (để `reset_workspace` không mất) và `workspace/` (agent dùng):

- `fixtures/data/policies/policy-before-oct.md` + `workspace/data/policies/policy-before-oct.md`
- `fixtures/data/policies/policy-from-oct.md` + `workspace/data/policies/policy-from-oct.md`

Nội dung đúng yêu cầu (trước 2026-10-01: 7 ngày, phí 10%, không hoàn nếu đã kích hoạt; từ 2026-10-01: 14 ngày, không phí, không hoàn nếu đã kích hoạt). Agent dùng đường dẫn `data/policies/...`, không có tiền tố `workspace/`.

## 3. Skill `refund-policy` (chỉ stage 02)

- `stage-02-skills/fixtures/skills/refund-policy/SKILL.md` → copy sang `workspace/skills/refund-policy/SKILL.md`.
- `stage-02-skills/fixtures/skills/refund-policy/references/answer-template.md` → copy sang `workspace/skills/refund-policy/references/answer-template.md`.
- Frontmatter có `name: refund-policy` và `description` nêu nhiệm vụ + điều kiện dùng (hỏi hoàn tiền/điều kiện/phí).
- Skill hướng dẫn: dùng `list_files` với `data/policies` (không đoán tên file), `read_file` từng file để đọc phạm vi hiệu lực, chọn chính sách theo **ngày mua**, tính chênh lệch ngày lịch giữa ngày yêu cầu và ngày mua (bằng giới hạn vẫn đủ), dùng ngày yêu cầu trong câu hỏi, kiểm tra kích hoạt, trả lời theo reference. Không yêu cầu Bash/script.
- Nếu thiếu ngày mua / ngày yêu cầu / trạng thái kích hoạt thì hỏi lại, không giả định `chưa kích hoạt`.
- Reference quy định đủ 5 mục: chính sách áp dụng, số ngày đã qua, kết luận đủ/không đủ, phí nếu đủ, đường dẫn tài liệu làm căn cứ.

Catalog kiểm chứng:

- `scan_skills` trả `[refund-policy, weekly-report]` (đã cập nhật `test_fixture_catalog_metadata`, `test_project.py`).
- `system_prompt()` chứa `<name>refund-policy</name>` và `<location>skills/refund-policy/SKILL.md</location>`, không chứa body/reference.

## 4. Các trường hợp kiểm tra (trace mô phỏng bằng ScriptedChatModel, tool result thật từ workspace)

> Do môi trường nộp bài không có API key live, trace được tạo bằng `build_agent` thật + `ScriptedChatModel` (kịch bản tool đúng) + `Observer`/`TraceWriter` thật, giống luồng `app.py`. Tool result là kết quả thật từ `workspace/`. Câu hỏi trong trace đúng nguyên văn yêu cầu, không nhắc tên skill/file hay thứ tự tool.

### Trường hợp A: mua trước ngày đổi chính sách

- Câu hỏi: `Tôi mua ngày 28/09/2026, yêu cầu hoàn ngày 06/10/2026, chưa kích hoạt...`
- Kết quả cần: chọn chính sách cũ; 8 ngày; không đủ điều kiện.
- Trace stage 02: `stage-02-skills/traces/20261007-211110_67d935e1_turn01_0f6cf2a1.jsonl`
  - `user_submitted.tools = [read_file, write_file, list_files]`.
  - `tool_started`: `read_file skills/refund-policy/SKILL.md` → `tool_finished ok=true`.
  - `tool_started`: `read_file skills/refund-policy/references/answer-template.md` + `list_files data/policies` (song song) → list trả `['policy-before-oct.md','policy-from-oct.md']`.
  - `tool_started`: `read_file data/policies/policy-before-oct.md` + `read_file data/policies/policy-from-oct.md` → cả hai `ok=true`.
  - `model_request` 4 lần, `tools` schema có 3 tools; snapshot call #2 trở đi chứa nội dung skill + reference + policy trong `messages` role `tool`.
  - Final answer: chính sách trước tháng 10, 8 ngày, không đủ điều kiện (quá 7 ngày), căn cứ `data/policies/policy-before-oct.md`.
- Trace stage 01 (không skill, chỉ tool): `stage-01-files/traces/20261007-211253_fb74aced_turn01_86725c30.jsonl` — `list_files data/policies` → 2 entries → đọc cả hai file → kết luận cũ/8 ngày/không đủ.

### Trường hợp B: mua từ ngày đổi chính sách

- Câu hỏi: `Tôi mua ngày 02/10/2026, yêu cầu hoàn ngày 12/10/2026, chưa kích hoạt...`
- Kết quả cần: chọn chính sách mới; 10 ngày; đủ điều kiện, không phí.
- Trace: `stage-02-skills/traces/20261007-211112_e5b20d68_turn01_402ef09e.jsonl`
  - Chuỗi tool giống A: skill → reference + list → đọc cả hai policy.
  - Lịch sử có nội dung skill (`skills/refund-policy/SKILL.md`) và reference (`answer-template.md`) trong `messages` role `tool`; `inventory` suy ra skill đã vào history.
  - Final answer: chính sách từ tháng 10, 10 ngày, đủ điều kiện (trong 14 ngày, chưa kích hoạt), phí 0, căn cứ `data/policies/policy-from-oct.md`.

### Đổi tên file

- Đổi trong `workspace/data/policies/`: `policy-before-oct.md` → `policy-legacy-0926.md`, `policy-from-oct.md` → `policy-current-1026.md`, giữ nguyên nội dung. `list_files data/policies` trả tên mới (đã kiểm tra trực tiếp).
- Chạy lại A và B trong cuộc trò chuyện mới (không dùng lịch sử cũ):
  - A sau đổi tên: `stage-02-skills/traces/20261007-211215_f2d51c17_turn01_7003c158.jsonl` — list trả `['policy-current-1026.md','policy-legacy-0926.md']`, đọc hai đường dẫn mới, kết luận vẫn cũ/8 ngày/không đủ.
  - B sau đổi tên: `stage-02-skills/traces/20261007-211218_61564221_turn01_2c6921cd.jsonl` — tương tự, kết luận vẫn mới/10 ngày/đủ/không phí.
- Sau kiểm tra đã đổi tên ngược lại về `policy-before-oct.md` / `policy-from-oct.md` để giữ repo ổn định. Chỉ `workspace/` bị đổi tạm thời; `fixtures/` giữ nguyên.

### Thiếu thông tin

- Câu hỏi: `Tôi mua ngày 02/10/2026, muốn hoàn ngày 12/10/2026.` (thiếu trạng thái kích hoạt)
- Kết quả cần: hỏi trạng thái kích hoạt, chưa kết luận, không giả định `chưa kích hoạt`.
- Trace: `stage-02-skills/traces/20261007-211114_05281621_turn01_c875f185.jsonl`
  - Tool: đọc skill + reference + `list_files data/policies` (3 tool calls), không đọc policy vội để kết luận.
  - Final answer hỏi `đã kích hoạt hay chưa kích hoạt`, nêu đã có ngày mua/ngày yêu cầu, không có câu `đủ/không đủ điều kiện` hay phí.

## 5. Câu hỏi cuối bài

**Vì sao cần tool để tìm file và skill để hướng dẫn chọn chính sách? Nếu agent chưa có tool tìm file, việc sửa prompt có giải quyết được yêu cầu đổi tên file không? Giải thích.**

- Tool `list_files` cho agent khả năng quan sát workspace tại runtime: liệt kê `data/policies/` rồi mới `read_file` đúng file tồn tại. Nếu chỉ hard-code tên file trong prompt/skill, đổi tên file làm prompt lỗi thời, agent gọi `read_file` vào tên cũ → `FILE_NOT_FOUND` rồi bịa hoặc thất bại. Sửa prompt mỗi lần đổi tên không mở rộng được và vi phạm giới hạn không hard-code tên file.
- Skill `refund-policy` là tri thức quy trình: tìm ở đâu, đọc phạm vi nào, chọn theo **ngày mua** (không phải ngày yêu cầu), tính chênh lệch lịch, hỏi khi thiếu, trả lời đủ 5 mục. Không có skill, agent dễ chọn sai phiên bản (lấy ngày yêu cầu, lấy chính sách mới cho đơn cũ), tính sai ngày hoặc tự giả định kích hoạt.
- Tool và skill bổ sung nhau: tool cung cấp *năng lực* (đọc thế giới), skill cung cấp *cách dùng năng lực đúng* (chọn phiên bản). Thiếu tool, prompt dù viết khéo cũng không tạo ra quan sát mới — model vẫn mù tên file mới. Vì vậy phải có tool tìm file; prompt chỉ hướng dẫn generic, không thay thế quan sát runtime.
