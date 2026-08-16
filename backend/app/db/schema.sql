-- Archivo consolidado de esquema para SQLite
-- Modo idempotente para producción (no borra datos en reinicios)

-- ==========================================
-- TABLAS DEL MODELO OPERACIONAL (desde database.sql)
-- ==========================================

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    nombre_completo TEXT,
    activo BOOLEAN DEFAULT 1,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS perfiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    preferencias TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    token_hash TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS asignaturas (
  codigo_programa INTEGER,
  nombre_programa TEXT,
  codigo_sede INTEGER,
  codigo_asignatura INTEGER,
  nombre_asignatura TEXT,
  id_semestre INTEGER,
  grupo TEXT,
  nombre_completo TEXT,
  correo_institucional TEXT
);

CREATE TABLE IF NOT EXISTS estudiantes (
  codigo_est INTEGER,
  primer_apellido TEXT,
  primer_nombre TEXT,
  programa_academico INTEGER,
  nombre_programa TEXT,
  codigo_sede INTEGER,
  nombre_sede TEXT,
  codigo_asignatura INTEGER,
  grupo TEXT,
  nombre_asignatura TEXT,
  pass TEXT
);

CREATE TABLE IF NOT EXISTS horarios (
  id_horario INTEGER PRIMARY KEY,
  codigo_asignatura INTEGER,
  grupo TEXT,
  fecha_tutoria TEXT,
  hora_inicio TEXT,
  hora_fin TEXT,
  tipo_tutoria TEXT
);

-- ==========================================
-- TABLAS DE LA BASE DE CONOCIMIENTO (desde el JSON)
-- ==========================================

CREATE TABLE IF NOT EXISTS sedes (
    codigo_sede INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    municipio TEXT NOT NULL,
    direccion TEXT,
    email TEXT,
    telefono TEXT,
    latitud REAL,
    longitud REAL
);

CREATE TABLE IF NOT EXISTS programas (
    codigo_programa INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    nivel_formacion TEXT NOT NULL,
    modalidad TEXT NOT NULL,
    snies TEXT,
    resolucion TEXT
);

CREATE TABLE IF NOT EXISTS info_fija (
    id_info INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT NOT NULL,
    subcategoria TEXT NOT NULL,
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    tags TEXT
);

-- Tabla virtual FTS5 para búsqueda semántica de la info_fija
CREATE VIRTUAL TABLE IF NOT EXISTS info_fija_fts USING fts5(
    titulo,
    contenido,
    tags,
    content='info_fija',
    content_rowid='id_info'
);

-- Triggers para mantener FTS5 sincronizado
CREATE TRIGGER IF NOT EXISTS tbl_ai_insert AFTER INSERT ON info_fija BEGIN
  INSERT INTO info_fija_fts(rowid, titulo, contenido, tags) VALUES (new.id_info, new.titulo, new.contenido, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS tbl_ai_delete AFTER DELETE ON info_fija BEGIN
  INSERT INTO info_fija_fts(info_fija_fts, rowid, titulo, contenido, tags) VALUES('delete', old.id_info, old.titulo, old.contenido, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS tbl_ai_update AFTER UPDATE ON info_fija BEGIN
  INSERT INTO info_fija_fts(info_fija_fts, rowid, titulo, contenido, tags) VALUES('delete', old.id_info, old.titulo, old.contenido, old.tags);
  INSERT INTO info_fija_fts(rowid, titulo, contenido, tags) VALUES (new.id_info, new.titulo, new.contenido, new.tags);
END;

CREATE TABLE IF NOT EXISTS respuestas_directas (
    id_respuesta INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta TEXT NOT NULL,
    pregunta_norm TEXT,
    respuesta TEXT NOT NULL,
    veces_usada INTEGER DEFAULT 0,
    categoria TEXT,
    origen TEXT,
    id_info INTEGER,
    FOREIGN KEY(id_info) REFERENCES info_fija(id_info)
);

-- ==========================================
-- TABLAS DEL CHAT
-- ==========================================

CREATE TABLE IF NOT EXISTS conversaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    titulo TEXT,
    activa BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversacion_id INTEGER,
    rol TEXT NOT NULL, -- 'user' o 'assistant'
    contenido TEXT NOT NULL,
    metadata_json TEXT,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversacion_id) REFERENCES conversaciones(id)
);

CREATE INDEX IF NOT EXISTS idx_estudiantes_codigo ON estudiantes(codigo_est);
CREATE INDEX IF NOT EXISTS idx_estudiantes_pass ON estudiantes(pass);
CREATE INDEX IF NOT EXISTS idx_asignaturas_codigo_grupo ON asignaturas(codigo_asignatura, grupo);
CREATE INDEX IF NOT EXISTS idx_horarios_asignatura_grupo ON horarios(codigo_asignatura, grupo);
CREATE INDEX IF NOT EXISTS idx_conversaciones_usuario ON conversaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion ON mensajes(conversacion_id);

-- ==========================================
-- TABLA DE METADATOS DE SINCRONIZACIÓN UIS
-- ==========================================

CREATE TABLE IF NOT EXISTS sync_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semestre TEXT NOT NULL,
    inicio_sync DATETIME NOT NULL,
    fin_sync DATETIME,
    estado TEXT NOT NULL, -- 'EN_PROCESO', 'EXITOSO', 'FALLIDO'
    programas_procesados INTEGER DEFAULT 0,
    sedes_procesadas INTEGER DEFAULT 0,
    asignaturas_actualizadas INTEGER DEFAULT 0,
    horarios_actualizados INTEGER DEFAULT 0,
    error_detalle TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_horarios_slot ON horarios(codigo_asignatura, grupo, fecha_tutoria, hora_inicio);
CREATE UNIQUE INDEX IF NOT EXISTS uq_asignaturas_curso ON asignaturas(codigo_programa, codigo_sede, codigo_asignatura, grupo, id_semestre);
