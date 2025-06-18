-- Create todo table in the cdc_db database
CREATE TABLE IF NOT EXISTS todos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate the todo table with initial data
INSERT INTO public.todos (title, description, completed)
VALUES
    ('Buy groceries', 'Milk, Bread, Eggs', FALSE),
    ('Walk the dog', 'Take the dog for a walk in the park', TRUE),
    ('Read a book', 'Finish reading "The Great Gatsby"', FALSE),
    ('Prepare dinner', 'Cook pasta and salad for dinner', FALSE),
    ('Call mom', 'Check in with mom and see how she is doing', TRUE);

-- Create a Debezium user with replication privileges
CREATE USER debezium_user WITH REPLICATION LOGIN PASSWORD 'debezium_password';

-- Grant necessary permissions to debezium_user
GRANT SELECT ON public.todos TO debezium_user;
GRANT USAGE ON SEQUENCE todos_id_seq TO debezium_user;
GRANT CONNECT ON DATABASE cdc_db TO debezium_user;
GRANT USAGE ON SCHEMA public TO debezium_user;

-- Create a publication for the todos table
CREATE PUBLICATION debezium_pub FOR TABLE todos;
