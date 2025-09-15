-- Initialize OCR database
-- This script is run when PostgreSQL container starts for the first time

-- Create additional schemas if needed
CREATE SCHEMA IF NOT EXISTS ocr_results;

-- Create table for storing OCR processing results
CREATE TABLE IF NOT EXISTS ocr_results.processing_history (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT,
    processing_time_ms FLOAT,
    success BOOLEAN NOT NULL,
    detected_text_count INTEGER DEFAULT 0,
    full_text TEXT,
    confidence_avg FLOAT,
    language VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_processing_history_created_at 
    ON ocr_results.processing_history(created_at);
CREATE INDEX IF NOT EXISTS idx_processing_history_success 
    ON ocr_results.processing_history(success);
CREATE INDEX IF NOT EXISTS idx_processing_history_filename 
    ON ocr_results.processing_history(filename);

-- Create table for storing individual text detections
CREATE TABLE IF NOT EXISTS ocr_results.text_detections (
    id SERIAL PRIMARY KEY,
    processing_id INTEGER REFERENCES ocr_results.processing_history(id) ON DELETE CASCADE,
    text_content TEXT NOT NULL,
    confidence FLOAT,
    confidence_level VARCHAR(10),
    bbox_x FLOAT,
    bbox_y FLOAT,
    bbox_width FLOAT,
    bbox_height FLOAT,
    detection_order INTEGER
);

-- Create index for text detections
CREATE INDEX IF NOT EXISTS idx_text_detections_processing_id 
    ON ocr_results.text_detections(processing_id);

-- Grant permissions to ocr_user
GRANT ALL PRIVILEGES ON SCHEMA ocr_results TO ocr_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ocr_results TO ocr_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ocr_results TO ocr_user;
