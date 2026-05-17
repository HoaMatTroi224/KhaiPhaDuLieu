-- Use after switching embeddings to
-- sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2.
--
-- Existing 768-dimensional embeddings are incompatible with the new
-- 384-dimensional model, so old chunks must be removed and regenerated.

TRUNCATE TABLE document_chunks;

ALTER TABLE document_chunks
ALTER COLUMN embedding TYPE vector(384);
