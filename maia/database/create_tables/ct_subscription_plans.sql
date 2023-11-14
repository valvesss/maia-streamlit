-- Create Table
CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    plan_name VARCHAR(255),
    max_interactions INT,
    max_bytes BIGINT,
    max_file_uploads INT,
    price NUMERIC(10, 2)
);

-- Fill table with trial plan
INSERT INTO 
    subscription_plans (plan_name, max_interactions, max_file_uploads, max_bytes, price)
VALUES ('trial', 50, 1, 25 * 1024 * 1024, 0); -- 25 MB is converted to bytes


--
INSERT INTO 
    subscription_plans (plan_name, max_interactions, max_file_uploads, max_bytes, price)
VALUES ('standard', 1000, 25, 1024 * 1024 * 1024, 100.00); -- 1GB is converted to bytes