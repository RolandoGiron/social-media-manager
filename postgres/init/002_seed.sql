-- Seed data for clinic CRM
-- Default dermatology tags and message templates

INSERT INTO tags (name, color) VALUES
    ('acne', '#ef4444'),
    ('rosacea', '#f97316'),
    ('limpieza-facial', '#22c55e'),
    ('postoperatorio', '#8b5cf6'),
    ('botox', '#ec4899'),
    ('depilacion-laser', '#06b6d4'),
    ('manchas', '#eab308'),
    ('revision-general', '#6366f1')
ON CONFLICT (name) DO NOTHING;

INSERT INTO message_templates (name, body, variables, category) VALUES
    ('bienvenida', 'Hola {{nombre}}, bienvenido/a a nuestra clinica. Estamos para servirte.', '{nombre}', 'general'),
    ('recordatorio-cita', 'Hola {{nombre}}, te recordamos tu cita el {{fecha}} a las {{hora}}. Te esperamos.', '{nombre,fecha,hora}', 'appointments'),
    ('promocion-general', 'Hola {{nombre}}, tenemos una promocion especial para ti: {{detalle}}. Responde SI para mas info.', '{nombre,detalle}', 'campaigns')
ON CONFLICT (name) DO NOTHING;
