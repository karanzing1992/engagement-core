CREATE TABLE IF NOT EXISTS mad_v1_source_chunks (upload_id TEXT NOT NULL,chunk_index INTEGER NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL,PRIMARY KEY(upload_id,chunk_index));
CREATE TABLE IF NOT EXISTS mad_v1_output_chunks (job_id TEXT NOT NULL,chunk_index INTEGER NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL,PRIMARY KEY(job_id,chunk_index));
