---
name: refund-policy
description: Tra cứu chính sách hoàn tiền theo ngày mua từ tài liệu trong workspace. Dùng khi người dùng hỏi về hoàn tiền, có được hoàn không, điều kiện hoàn hoặc phí hoàn.
---

# Refund policy

Tra cứu chính sách hoàn tiền đúng phiên bản theo ngày mua, không đoán từ kiến thức sẵn có.

## Khi nào dùng

Khi người dùng hỏi về hoàn tiền, đủ điều kiện hoàn hay phí hoàn thì đọc skill này trước khi làm.

## Thu thập thông tin

Cần đủ 3 thông tin trước khi kết luận:

- ngày mua
- ngày yêu cầu hoàn
- trạng thái kích hoạt (đã kích hoạt hay chưa kích hoạt)

Nếu thiếu bất kỳ thông tin nào, hỏi lại trước khi kết luận. Không tự giả định trạng thái kích hoạt, không tự lấy ngày hiện tại của máy làm ngày yêu cầu.

## Các bước

1. Dùng `list_files` với `path` là `data/policies` để liệt kê tài liệu chính sách. Không đoán tên file, vì tên file có thể thay đổi.
2. Dùng `read_file` đọc nội dung từng file tìm được để xác định phạm vi hiệu lực theo ngày mua và điều kiện hoàn (số ngày tối đa, phí, điều kiện kích hoạt).
3. Chọn đúng một chính sách có phạm vi hiệu lực chứa ngày mua. Ngày mua là căn cứ chọn phiên bản, không phải ngày yêu cầu hoàn.
4. Tính số ngày đã qua là chênh lệch ngày lịch giữa ngày yêu cầu hoàn và ngày mua. Bằng đúng giới hạn vẫn đủ điều kiện về thời gian. Dùng ngày yêu cầu trong câu hỏi, không dùng ngày hiện tại của máy.
5. Áp dụng điều kiện kích hoạt trong chính sách đã chọn: nếu sản phẩm đã kích hoạt thì không đủ điều kiện, bất kể số ngày.
6. So sánh số ngày đã qua với giới hạn trong chính sách đã chọn để kết luận đủ hoặc không đủ điều kiện về thời gian.
7. Trả lời theo `references/answer-template.md` trong thư mục skill này, tức `skills/refund-policy/references/answer-template.md`. Dẫn đường dẫn tài liệu đã đọc làm căn cứ.

## Quy tắc

- Mọi kết luận phải dựa trên nội dung `read_file` thành công, không dựa trên tên file hay kiến thức sẵn có.
- Không yêu cầu Bash hoặc script.
