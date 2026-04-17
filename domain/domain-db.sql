-- ==========================================================
-- 1. DDL: CRIAÇÃO DA ESTRUTURA (SCHEMA)
-- ==========================================================

-- Limpeza inicial (remove as tabelas se já existirem para recriar do zero)
DROP TABLE IF EXISTS video_youtube CASCADE;
DROP TABLE IF EXISTS video_upload CASCADE;
DROP TABLE IF EXISTS pdf CASCADE;
DROP TABLE IF EXISTS exercise CASCADE;
DROP TABLE IF EXISTS domain CASCADE;
DROP TABLE IF EXISTS rag_library CASCADE;

-- 1. Tabela Domain (Tabela Pai)
CREATE TABLE domain (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);

-- 2. Tabela Exercise
CREATE TABLE exercise (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    options JSONB NOT NULL, 
    correct VARCHAR(10) NOT NULL,
    domain_id INTEGER NOT NULL,
    
    CONSTRAINT fk_domain_exercise 
        FOREIGN KEY (domain_id) 
        REFERENCES domain (id) 
        ON DELETE CASCADE
);

-- 3. Tabela VideoUpload
CREATE TABLE video_upload (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    domain_id INTEGER NOT NULL,

    CONSTRAINT fk_domain_video_upload 
        FOREIGN KEY (domain_id) 
        REFERENCES domain (id) 
        ON DELETE CASCADE
);

-- 4. Tabela VideoYoutube
CREATE TABLE video_youtube (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    domain_id INTEGER NOT NULL,

    CONSTRAINT fk_domain_video_youtube 
        FOREIGN KEY (domain_id) 
        REFERENCES domain (id) 
        ON DELETE CASCADE
);

-- 5. Tabela PDF
CREATE TABLE pdf (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    domain_id INTEGER NOT NULL,

    CONSTRAINT fk_domain_pdf 
        FOREIGN KEY (domain_id) 
        REFERENCES domain (id) 
        ON DELETE CASCADE
);

-- Criação da tabela para a Base de Conhecimento do Agente (RAG)
CREATE TABLE rag_library (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    path VARCHAR(500) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- 2. DML: POPULAÇÃO DOS DADOS (INSERTS)
-- ==========================================================

-- ----------------------------------------------------------
-- DOMÍNIO 1: Fremeworks
-- ----------------------------------------------------------

-- Inserção do arquivo "Padrão Pedagógico"
INSERT INTO rag_library (filename, path, description) 
VALUES (
    'Padrão Pedagogico-SessaoEnsino-FA_PorT-SBIE2007-LEASPE.pdf', 
    'https://f32aymnyqlp1vubu.public.blob.vercel-storage.com/Padr%C3%A3o%20Pedagogico-SessaoEnsino-FA_PorT-SBIE2007-LEASPE.pdf',
    'Artigo sobre estratégias de ensino de IA: recomenda uso de Debate Sincrono para fixação e Reuso de materiais. A nota deve valorizar a interatividade.'
),
(
    'Execucao de uma Sessao de Ensino.pdf', 
    'https://f32aymnyqlp1vubu.public.blob.vercel-storage.com/Execucao%20de%20uma%20Sessao%20de%20Ensino.pdf',
    'Uma sessão de ensino contem uma estratégia e cada estratégia é composta de varias táticas.'
);


INSERT INTO domain (name, description) 
VALUES ('Fremeworks', 'Como aprender um framework?
Por isso, vamos abordar neste artigo alguns pontos sobre quando é o momento ideal para se aventurar nos frameworks.

    Construa primeiro uma base sólida na linguagem. ...
    Tente resolver problemas sem utilizar frameworks. ...
    Identifique a necessidade. ...
    Não se esqueça do equilíbrio');

-- PDFs do Domínio 1 (ID assume ser 1)
-- Nota: O caminho /app/app/uploads/ é o padrão dentro do container Docker conforme seu código python
INSERT INTO pdf (filename, path, domain_id) VALUES 
('Paper-2024-AgentDesignPatternCatalogue.pdf', 'https://f32aymnyqlp1vubu.public.blob.vercel-storage.com/Paper-2024-AgentDesignPatternCatalogue.pdf', 1),
('Paper-Agents-2024-Ignise.pdf', 'https://f32aymnyqlp1vubu.public.blob.vercel-storage.com/Paper-Agents-2024-Ignise.pdf', 1);

-- Vídeos YouTube do Domínio 1
INSERT INTO video_youtube (url, domain_id) VALUES 
('https://www.youtube.com/watch?v=BQ35b4b8qi4&t=616s', 1),
('https://www.youtube.com/watch?v=MQUP3ML8Sjs', 1);

-- Vídeo Uploaded do Domínio 1
INSERT INTO video_upload (filename, path, domain_id) VALUES 
('2025-12-19_09-57-13.mp4', 'https://f32aymnyqlp1vubu.public.blob.vercel-storage.com/2025-12-19_09-57-13.mp4', 1);

-- Exercícios do Domínio 1
-- As opções e respostas foram geradas baseadas no contexto das perguntas fornecidas.
INSERT INTO exercise (question, options, correct, domain_id) VALUES 
(
    'Em frameworks front-end modernos (como React, Vue ou Angular), o conceito de "reatividade" é central. Qual das alternativas abaixo descreve corretamente o comportamento de um framework reativo ao detectar uma mudança no estado (state) de um componente?', 
    '["O framework exige que o desenvolvedor recarregue a página manualmente.", "O framework atualiza automaticamente apenas as partes da interface (DOM) que dependem daquele estado.", "O framework apaga o componente e cria um novo do zero, perdendo dados não salvos.", "O framework converte o código para HTML estático e para de responder a eventos."]', 
    '1', -- Resposta correta: Índice 1 (O framework atualiza automaticamente...)
    1
),
(
    'Ao utilizar frameworks de back-end como Spring Boot (Java) ou NestJS (Node.js) para criar APIs REST, o desenvolvedor frequentemente utiliza "Decorators" ou "Annotations" (ex: @GetMapping, @Post). Qual é a principal função desse recurso?', 
    '["Apenas comentar o código para documentação.", "Configurar metadados, como rotas, injeção de dependência e validações, de forma declarativa.", "Aumentar a performance do processador do servidor.", "Substituir a necessidade de escrever classes e funções."]', 
    '1', -- Resposta correta: Índice 1 (Configurar metadados...)
    1
),
(
    'Frameworks de estilização como o Tailwind CSS ganharam muita popularidade em 2024 e 2025. Qual é a característica principal da abordagem "Utility-First" proposta por esse tipo de ferramenta?', 
    '["O uso de classes utilitárias de baixo nível que permitem construir designs diretamente no HTML.", "A obrigatoriedade de escrever arquivos CSS separados para cada componente.", "O fornecimento de componentes prontos (como botões e navbars) idênticos ao Bootstrap.", "A proibição do uso de design responsivo."]', 
    '0', -- Resposta correta: Índice 0 (O uso de classes utilitárias...)
    1
);


-- ----------------------------------------------------------
-- DOMÍNIO 2: C++
-- ----------------------------------------------------------

INSERT INTO domain (name, description) 
VALUES ('C++', 'C++ é uma linguagem de programação poderosa, de propósito geral e de alto desempenho, criada como uma extensão da linguagem C, oferecendo controle de baixo nível sobre o hardware e suporte multi-paradigma (orientada a objetos, genérica, imperativa).');

-- PDFs do Domínio 2 (ID assume ser 2)
INSERT INTO pdf (filename, path, domain_id) VALUES 
('Le_Prototype_BIRDS.pdf', 'https://f32aymnyqlp1vubu.public.blob.vercel-storage.com/Le_Prototype_BIRDS.pdf', 2),
('Relatorio_Reuso-comLinkVideo.pdf', 'https://f32aymnyqlp1vubu.public.blob.vercel-storage.com/Relatorio_Reuso-comLinkVideo.pdf', 2);

-- Vídeos YouTube do Domínio 2
INSERT INTO video_youtube (url, domain_id) VALUES 
('https://www.youtube.com/watch?v=N-VMAIvm3W4', 2),
('https://www.youtube.com/watch?v=4p7axLXXBGU', 2);

-- Vídeo Uploaded do Domínio 2
INSERT INTO video_upload (filename, path, domain_id) VALUES 
('2025-12-19_10-13-32.mp4', 'https://f32aymnyqlp1vubu.public.blob.vercel-storage.com/2025-12-19_10-13-32.mp4', 2);

-- Exercícios do Domínio 2
INSERT INTO exercise (question, options, correct, domain_id) VALUES 
(
    'Qual será a saída do seguinte trecho de código em C++: cout << 10 + 20;', 
    '["1020", "30", "Erro de compilação", "0"]', 
    '1', -- Resposta correta: Índice 1 (30)
    2
),
(
    'No contexto de Programação Orientada a Objetos em C++, o que define uma classe abstrata?', 
    '["Uma classe que não possui construtor.", "Uma classe que possui apenas atributos privados.", "Uma classe que não pode ser instanciada diretamente e possui pelo menos uma função virtual pura.", "Uma classe que herda de múltiplas classes base."]', 
    '2', -- Resposta correta: Índice 2 (Uma classe que não pode ser instanciada...)
    2
),
(
    'Considere o uso de Smart Pointers (Ponteiros Inteligentes) introduzidos a partir do C++11. Qual das alternativas descreve corretamente o comportamento do std::unique_ptr?', 
    '["Permite que múltiplos ponteiros apontem para o mesmo objeto simultaneamente.", "Gerencia a memória automaticamente garantindo posse (ownership) exclusiva de um recurso.", "Não libera a memória automaticamente, exigindo o uso de delete.", "É utilizado apenas para array de caracteres."]', 
    '1', -- Resposta correta: Índice 1 (Gerencia a memória automaticamente...)
    2
);