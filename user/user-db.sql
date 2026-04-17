-- ==========================================================
-- 1. DDL: CRIAÇÃO DA ESTRUTURA (SCHEMA)
-- ==========================================================

DROP TABLE IF EXISTS student CASCADE;
DROP TABLE IF EXISTS teacher CASCADE;

CREATE TABLE student(
    student_id INT GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(100),
    course VARCHAR(100),
    type VARCHAR(20),
    age SMALLINT,
    username VARCHAR(80),
    email VARCHAR(80),
    password_hash VARCHAR(128),
    -- NOVAS COLUNAS PARA O PERFIL DE APRENDIZADO
    pref_content_type VARCHAR(50),      -- Ex: 'teoria', 'exemplos', 'exercicios'
    pref_communication VARCHAR(50),     -- Ex: 'chat', 'video', 'none'
    pref_receive_email BOOLEAN,         -- Ex: TRUE ou FALSE
    PRIMARY KEY (student_id)
);

CREATE TABLE teacher(
    teacher_id INT GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(100),
    course VARCHAR(100),
    type VARCHAR(20),
    age SMALLINT,
    username VARCHAR(80),
    email VARCHAR(80),
    password_hash VARCHAR(128),
    PRIMARY KEY (teacher_id)
);

CREATE TABLE student_feedback (
    id SERIAL PRIMARY KEY,
    student_username VARCHAR(100) NOT NULL,
    session_id INTEGER, -- Opcional, para saber de qual aula foi
    domain_name VARCHAR(100),
    feedback_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- 2. DML: POPULAÇÃO DOS DADOS (INSERTS)
-- ==========================================================

-- Inserindo Student (ID 1)
INSERT INTO student (student_id, name, course, type, age, username, email, password_hash, pref_content_type, pref_communication, pref_receive_email)
OVERRIDING SYSTEM VALUE 
VALUES 
(1, 'Kelvin', 'CC', 'student', 22, 'kelvin', 'kelvin@email.com', 'hash', 'exemplos', 'chat', TRUE),
(2, 'Maria', 'CC', 'student', 21, 'maria', 'maria@email.com', 'hash', 'teoria', 'video', TRUE),
(3, 'João', 'CC', 'student', 23, 'joao', 'joao@email.com', 'hash', 'exercicios', 'video', FALSE),
(4, 'Ana', 'CC', 'student', 20, 'ana', 'ana@email.com', 'hash', 'exemplos', 'chat', TRUE);

-- Inserindo Teacher (ID 1)
INSERT INTO teacher (teacher_id, name, course, type, age, username, email, password_hash)
OVERRIDING SYSTEM VALUE 
VALUES (1, 'kelvin123', NULL, 'teacher', 33, 'kelvin123', 'ksal@ic.ufal.br', '88092018');

-- ==========================================================
-- 3. RESET DE SEQUÊNCIAS
-- ==========================================================
-- Importante para garantir que o próximo insert automático seja ID 2, e não tente usar o 1 de novo.

SELECT setval(pg_get_serial_sequence('student', 'student_id'), (SELECT MAX(student_id) FROM student));
SELECT setval(pg_get_serial_sequence('teacher', 'teacher_id'), (SELECT MAX(teacher_id) FROM teacher));