-- ==========================================================
-- 1. DDL: CRIAÇÃO DA ESTRUTURA (SCHEMA)
-- ==========================================================

DROP TABLE IF EXISTS verified_answers CASCADE;
DROP TABLE IF EXISTS extra_notes CASCADE;
DROP TABLE IF EXISTS session_strategies CASCADE;
DROP TABLE IF EXISTS session_teachers CASCADE;
DROP TABLE IF EXISTS session_students CASCADE;
DROP TABLE IF EXISTS session_domains CASCADE;
DROP TABLE IF EXISTS session CASCADE;

-- Tabela Session
CREATE TABLE session (
    id SERIAL PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    start_time TIMESTAMP,
    current_tactic_index INTEGER DEFAULT 0,
    current_tactic_started_at TIMESTAMP,
    original_strategy_id VARCHAR(50),
    use_agent BOOLEAN DEFAULT FALSE
);

-- Tabelas normalizadas (Relacionamentos)
CREATE TABLE session_strategies (
    session_id INTEGER NOT NULL,
    strategy_id VARCHAR(50) NOT NULL,
    PRIMARY KEY (session_id, strategy_id),
    CONSTRAINT fk_session_strategies
        FOREIGN KEY (session_id) REFERENCES session (id) ON DELETE CASCADE
);

CREATE TABLE session_teachers (
    session_id INTEGER NOT NULL,
    teacher_id VARCHAR(50) NOT NULL,
    PRIMARY KEY (session_id, teacher_id),
    CONSTRAINT fk_session_teachers
        FOREIGN KEY (session_id) REFERENCES session (id) ON DELETE CASCADE
);

CREATE TABLE session_students (
    session_id INTEGER NOT NULL,
    student_id VARCHAR(50) NOT NULL,
    PRIMARY KEY (session_id, student_id),
    CONSTRAINT fk_session_students
        FOREIGN KEY (session_id) REFERENCES session (id) ON DELETE CASCADE
);

CREATE TABLE session_domains (
    session_id INTEGER NOT NULL,
    domain_id VARCHAR(50) NOT NULL,
    PRIMARY KEY (session_id, domain_id),
    CONSTRAINT fk_session_domains
        FOREIGN KEY (session_id) REFERENCES session (id) ON DELETE CASCADE
);

-- Tabela ExtraNotes
CREATE TABLE extra_notes (
    id SERIAL PRIMARY KEY,
    estudante_username VARCHAR(100) NOT NULL,
    student_id INTEGER NOT NULL,
    extra_notes FLOAT NOT NULL DEFAULT 0.0,
    session_id INTEGER NOT NULL,
    CONSTRAINT fk_session_extra_notes
        FOREIGN KEY (session_id) REFERENCES session (id) ON DELETE CASCADE
);

-- Tabela VerifiedAnswers
CREATE TABLE verified_answers (
    id SERIAL PRIMARY KEY,
    student_name VARCHAR(100) NOT NULL,
    student_id VARCHAR(50) NOT NULL, 
    answers JSONB NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    session_id INTEGER NOT NULL,
    CONSTRAINT fk_session_verified_answers
        FOREIGN KEY (session_id) REFERENCES session (id) ON DELETE CASCADE
);

-- ==========================================================
-- 2. DML: POPULAÇÃO DOS DADOS (INSERTS)
-- ==========================================================

-- Inserindo Sessões
INSERT INTO session (status, code, start_time, current_tactic_index, current_tactic_started_at, original_strategy_id, use_agent)
VALUES
('aguardando',  'CODE1234', NULL, 0, NULL, NULL, FALSE),
('in-progress', 'LIVE5678', NOW(), 1, NOW(), NULL, FALSE),
('finished',    'DONE9012', NOW() - INTERVAL '2 hour', 5, NOW() - INTERVAL '1 hour', NULL, FALSE);

-- Vinculando Estratégias
INSERT INTO session_strategies (session_id, strategy_id) VALUES
(1, '1'),
(2, '3'),
(3, '2');

-- Vinculando Professores
INSERT INTO session_teachers (session_id, teacher_id) VALUES
(1, '1'),
(2, '1'),
(3, '1');

-- Vinculando Alunos
INSERT INTO session_students (session_id, student_id) VALUES
(1, '1'),
(2, '1'),
(3, '1');

-- Vinculando Domínios
INSERT INTO session_domains (session_id, domain_id) VALUES
(1, '1'),
(2, '1'),
(3, '2');

-- Inserindo Notas Extras
INSERT INTO extra_notes (estudante_username, student_id, extra_notes, session_id) VALUES
('aluno_demo', 1, 9.5, 2),
('aluno_demo', 1, 8.0, 3);

-- Inserindo Respostas Verificadas
INSERT INTO verified_answers (student_name, student_id, answers, score, session_id) VALUES
('aluno_demo', '1', '[{"exercise_id": 101, "answer": 2, "correct": true}, {"exercise_id": 102, "answer": 0, "correct": false}]'::jsonb, 50, 2);