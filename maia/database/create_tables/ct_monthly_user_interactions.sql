CREATE TABLE monthly_user_interactions (
    user_id UUID REFERENCES users(id),
    month_year DATE,  -- first day of the month, e.g., '2023-11-01'
    interactions_count INT,
    file_uploads_count INT,
    PRIMARY KEY(user_id, month_year)
);