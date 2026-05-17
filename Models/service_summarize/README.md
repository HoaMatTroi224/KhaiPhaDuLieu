# service_summarize

FastAPI service tóm tắt bài báo khoa học tiếng Việt, sử dụng **ViT5-base** được fine-tune với LoRA adapter.

---

## Kiến trúc

```
Input text / PDF
      │
      ▼
 PDF Extractor (PyMuPDF)
      │
      ▼
 Map-Reduce Summarizer
  ├─ Split thành chunks (~874 tokens/chunk)
  ├─ Tóm tắt từng chunk song song (Map)
  └─ Tổng hợp thành bản tóm tắt cuối (Reduce)
      │
      ▼
   ViT5-base + LoRA Adapter
```

## Test API

### Swagger UI (trình duyệt)

## Mở: **https://vit5-summarize-954130532427.us-central1.run.app/docs**

## Lưu ý quan trọng

> **Model chỉ hỗ trợ tiếng Việt.**
> ViT5 được fine-tune trên tập dữ liệu bài báo khoa học tiếng Việt.
> Nếu input là tiếng Anh, output sẽ không có ý nghĩa.

| Thông số            | Giá trị                                 |
| ------------------- | --------------------------------------- |
| Ngôn ngữ hỗ trợ     | Tiếng Việt                              |
| Độ dài input tối đa | 20.000 ký tự                            |
| Độ dài output       | 80–512 tokens                           |
| Inference           | CPU (không cần GPU)                     |
| Thời gian xử lý     | ~15s (text ngắn) / ~250s (PDF dài, CPU) |
