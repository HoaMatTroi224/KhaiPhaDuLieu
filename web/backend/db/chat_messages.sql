ALTER TABLE public.chat_history
ADD COLUMN IF NOT EXISTS citations jsonb,
ADD COLUMN IF NOT EXISTS chunks_retrieved integer,
ADD COLUMN IF NOT EXISTS fact_check jsonb;
