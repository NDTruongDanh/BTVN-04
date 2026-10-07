---
title: "Tra cứu chính sách đúng phiên bản"
source: "https://pub.nndkhoa9.win/agentic-ai-engineering/d05-tool-use-skill-use/exercise-block-1.html"
author:
published:
created: 2026-10-07
description:
tags:
  - "clippings"
---

**Tìm tài liệu** Liệt kê thư mục bằng tool

**Chọn chính sách** Áp dụng theo ngày mua

**Kiểm tra kết quả** Đối chiếu trace và tài liệu

## Thêm tool tìm tài liệu và skill tra cứu

Project mẫu chưa có tool liệt kê thư mục. Bạn phải cài đặt tool này, đăng ký cho agent và viết một skill mới. Agent cần tìm được tài liệu ngay cả khi tên file thay đổi.

**Giới hạn thay đổi:** được sửa mã nguồn tool và phần đăng ký tool. Không viết cố định tên file, nội dung chính sách hoặc đáp án trong system prompt hay mã nguồn tool.

01 / CHUẨN BỊ

## Dữ liệu chính sách

Dùng lab tại `demo/agent-tools-skills-lab/`. Làm trên bản sao các stage, giữ nguyên project mẫu. Dùng môi trường và cấu hình model đã thiết lập trong phần giảng.

Ở bản sao stage 01 và stage 02, tạo hai file dưới `workspace/data/policies/`. Đường dẫn agent sử dụng là `data/policies/`, không có tiền tố `workspace/`.

### policy-before-oct.md

```
# Chính sách hoàn tiền trước tháng 10
Áp dụng cho ngày mua trước 2026-10-01.
Được yêu cầu hoàn tiền trong 7 ngày kể từ ngày mua.
Phí hoàn tiền: 10% giá trị đơn hàng.
Không hoàn tiền nếu sản phẩm đã kích hoạt.
```

### policy-from-oct.md

```
# Chính sách hoàn tiền từ tháng 10
Áp dụng cho ngày mua từ 2026-10-01, bao gồm ngày này.
Được yêu cầu hoàn tiền trong 14 ngày kể từ ngày mua.
Không thu phí hoàn tiền.
Không hoàn tiền nếu sản phẩm đã kích hoạt.
```

**Quy ước:** số ngày là chênh lệch ngày lịch giữa ngày yêu cầu hoàn và ngày mua. Bằng đúng giới hạn vẫn đủ điều kiện về thời gian. Dùng ngày yêu cầu trong câu hỏi, không dùng ngày hiện tại của máy.

02 / THỰC HIỆN

## Các bước thực hiện

### Stage 00 / 2 phút: Xác định giới hạn của agent

Gửi câu hỏi ở trường hợp A, không dán nội dung chính sách vào chat. Ghi lại thông tin và khả năng agent còn thiếu để trả lời. Kiểm tra agent có kết quả đọc tài liệu hay chỉ trả lời từ kiến thức sẵn có.

### Stage 01 / 8 phút: Cài đặt tool list_files

```
list_files(path: str) → kết quả liệt kê thư mục
```

- Liệt kê các mục trực tiếp trong thư mục, không duyệt đệ quy.
- Mỗi mục có tên, đường dẫn tương đối với workspace và loại `file` hoặc `directory`. Sắp xếp theo tên để kết quả ổn định.
- Tái sử dụng cách xử lý đường dẫn và cấu trúc kết quả/lỗi của tool file hiện có. Chỉ truy cập trong workspace, kể cả khi có `..`, đường dẫn tuyệt đối hoặc symlink dẫn ra ngoài.
- Đường dẫn không tồn tại hoặc là file phải trả lỗi rõ ràng, không trả danh sách rỗng như thể thư mục hợp lệ.
- Đăng ký tool để xuất hiện trong schema tools gửi model. Agent dùng `list_files` để tìm rồi dùng `read_file` để đọc tài liệu.

### Stage 02 / 10 phút: Thêm tool đã viết và tạo skill refund-policy

```
workspace/skills/refund-policy/
  SKILL.md
  references/answer-template.md
```

- Frontmatter có `name` và `description`. Trường `description` nêu nhiệm vụ và điều kiện sử dụng skill.
- Skill hướng dẫn tìm tài liệu trong `data/policies/`, đọc phạm vi hiệu lực và chọn chính sách theo **ngày mua**.
- Nếu thiếu ngày mua, ngày yêu cầu hoàn hoặc trạng thái kích hoạt, hỏi lại trước khi kết luận.
- Reference quy định câu trả lời có: chính sách áp dụng, số ngày đã qua, kết luận đủ/không đủ điều kiện, phí nếu đủ điều kiện và đường dẫn tài liệu làm căn cứ.
- Không yêu cầu Bash hoặc script vì stage 02 chưa có khả năng đó.

Tải lại trang để cập nhật catalog, mở cuộc trò chuyện mới và gửi câu hỏi ở phần kiểm tra. Không nhắc tên skill, tên file hoặc chỉ định thứ tự gọi tool trong câu hỏi.

03 / KIỂM TRA

## Các trường hợp kiểm tra

### Trường hợp A: mua trước ngày đổi chính sách

```
Tôi mua ngày 28/09/2026, yêu cầu hoàn ngày 06/10/2026,
chưa kích hoạt. Tôi có được hoàn không?
```

### Trường hợp B: mua từ ngày đổi chính sách

```
Tôi mua ngày 02/10/2026, yêu cầu hoàn ngày 12/10/2026,
chưa kích hoạt. Tôi có được hoàn không?
```

| Trường hợp      | Kết quả cần đạt                                                                                          | Bằng chứng cần kiểm tra                                                             |
| --------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| A               | Chọn chính sách cũ; 8 ngày; không đủ điều kiện.                                                          | Tool tìm file, đọc chính sách cũ; câu trả lời dẫn đúng tài liệu.                    |
| B               | Chọn chính sách mới; 10 ngày; đủ điều kiện, không phí.                                                   | Lịch sử có nội dung skill và reference; câu trả lời dẫn đúng tài liệu.              |
| Đổi tên file    | Đổi tên hai file, giữ nội dung rồi chạy lại trường hợp A và B. Kết luận không thay đổi.                  | Cuộc trò chuyện mới tìm được file đã đổi tên, không sử dụng tài liệu từ lịch sử cũ. |
| Thiếu thông tin | Hỏi “Tôi mua ngày 02/10/2026, muốn hoàn ngày 12/10/2026.” Agent hỏi trạng thái kích hoạt, chưa kết luận. | Không tự giả định “chưa kích hoạt”.                                                 |

### Kiểm tra tool trực tiếp

Gọi tool với một thư mục hợp lệ, một đường dẫn file, một đường dẫn không tồn tại và một đường dẫn vượt workspace. Ba trường hợp sau phải trả lỗi. Chỉ dùng dữ liệu giả, không thử đọc thông tin cá nhân hoặc thông tin bí mật.

04 / NỘP BÀI

## Yêu cầu nộp bài

- Mã nguồn tool mới và phần đăng ký tool ở stage 01, stage 02.
- Thư mục skill `refund-policy/` và hai tài liệu chính sách.
- Trace cho trường hợp A, trường hợp B sau khi đổi tên file và trường hợp thiếu thông tin. Không nộp `.env` hay API key.
- `analysis.md`: kết quả kiểm tra tool, kết quả từng trường hợp và vị trí bằng chứng trong trace.

**Câu hỏi cuối bài:** vì sao cần tool để tìm file và skill để hướng dẫn chọn chính sách? Nếu agent chưa có tool tìm file, việc sửa prompt có giải quyết được yêu cầu đổi tên file không? Giải thích.
