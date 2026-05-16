CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'indexed', 'failed');

CREATE TYPE document_type AS ENUM ('pdf', 'txt', 'docx');

-- -- =====================================================
-- -- 1. USERS
-- -- =====================================================
-- CREATE TABLE public.users (
--   id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
--   username varchar UNIQUE NOT NULL,
--   password varchar NOT NULL,
--   email varchar UNIQUE NOT NULL,
--   full_name varchar,
--   status boolean DEFAULT true,
--   last_login timestamptz,
--   created_at timestamptz DEFAULT now()
-- );

-- =====================================================
-- 1. USERS
-- =====================================================
CREATE TABLE public.users (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username varchar UNIQUE NOT NULL,
  password varchar NOT NULL,
  email varchar UNIQUE NOT NULL,
  full_name varchar,
  status boolean DEFAULT true,
  last_login timestamptz,
  created_at timestamptz DEFAULT now()
);


-- =====================================================
-- 2. PAPERS (Kho bài báo hệ thống - huấn luyện / kiểm thử)
-- =====================================================
CREATE TABLE public.papers (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title text,
  authors text,
  abstract text,
  content text,
  publication_date date,
  category text,
  source_url text UNIQUE,
  created_at timestamptz DEFAULT now()
);

-- =====================================================
-- 3. PROJECTS (Dự án của người dùng)
-- =====================================================
CREATE TABLE public.projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  domain text,
  description text,
  collection_name text UNIQUE NOT NULL,  -- Tên collection trong Vector DB
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.projects
ADD COLUMN is_draft boolean NOT NULL DEFAULT true;

-- =====================================================
-- 4. DOCUMENTS (Tài liệu người dùng tải lên, thuộc về một Project)
-- =====================================================
CREATE TABLE public.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  
  -- Metadata file
  file_url text,
  file_name text,
  file_type document_type,
  upload_time timestamptz DEFAULT now(),
  status document_status DEFAULT 'uploaded',
  is_private boolean DEFAULT true,
  
  -- Thông tin trích xuất từ tài liệu
  title text,
  authors text,
  publication_date date,
  extracted_content text,
  full_content text,
  key_words text
);

ALTER TABLE public.documents
ADD COLUMN file_path text;

ALTER TABLE public.documents
ADD COLUMN file_size bigint;

CREATE INDEX idx_documents_project ON public.documents(project_id);


-- =====================================================
-- 5. SUMMARIES
-- =====================================================
CREATE TABLE public.summaries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

  document_id uuid REFERENCES public.documents(id) ON DELETE CASCADE,
  
  summary_text text NOT NULL,
  summary_type text, -- 'short', 'detailed', 'bullet'
  original_text text,
  
  created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_summaries_document ON public.summaries(document_id);

-- =====================================================
-- 6. CHAT HISTORY
-- =====================================================
CREATE TABLE public.chat_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  thread_id uuid NOT NULL,        -- Tất cả message trong cùng một thread có giá trị này giống nhau
  
  role varchar(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content text NOT NULL,
  citations jsonb,
  chunks_retrieved integer,
  fact_check jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_chat_history_thread ON public.chat_history(thread_id);

ALTER TABLE public.chat_history
ADD COLUMN IF NOT EXISTS citations jsonb,
ADD COLUMN IF NOT EXISTS chunks_retrieved integer,
ADD COLUMN IF NOT EXISTS fact_check jsonb;

-- =====================================================
-- 7. NOTES
-- =====================================================
CREATE TABLE public.notes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  
  document_id uuid REFERENCES public.documents(id) ON DELETE CASCADE,
  
  title varchar,
  content text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
