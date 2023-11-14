-- DROP FUNCTION increment_user_monthly_ai_interactions(UUID)
CREATE OR REPLACE FUNCTION increment_user_monthly_ai_interactions(p_user_id UUID)
RETURNS JSON LANGUAGE plpgsql AS $$
DECLARE
    current_month DATE := date_trunc('month', CURRENT_DATE);
    existing_record BOOLEAN;
BEGIN
    -- Check if a record for the current month already exists
    SELECT EXISTS (
        SELECT 1
        FROM monthly_user_interactions
        WHERE user_id = p_user_id AND month_year = current_month
    ) INTO existing_record;
    
    IF existing_record THEN
        -- If a record exists, increment the interactions_count
        UPDATE monthly_user_interactions
        SET interactions_count = interactions_count + 1
        WHERE user_id = p_user_id AND month_year = current_month;
    ELSE
        -- If no record exists, create a new record with interactions_count = 1
        INSERT INTO monthly_user_interactions (user_id, month_year, interactions_count)
        VALUES (p_user_id, current_month, 1);
    END IF;

    -- Return a success message as a JSON object
    RETURN json_build_object('success', true, 'incremented_user_monthly_ai_interactions', 1);
END;
$$;