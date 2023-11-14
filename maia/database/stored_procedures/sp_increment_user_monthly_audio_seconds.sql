-- DROP FUNCTION increment_user_monthly_ai_interactions(UUID)
CREATE OR REPLACE FUNCTION increment_user_monthly_audio_seconds(p_user_id UUID, p_seconds INTEGER)
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
        -- If a record exists, increment the audio_seconds_count
        UPDATE monthly_user_interactions
        SET audio_seconds_count = COALESCE(audio_seconds_count, 0) + p_seconds
        WHERE user_id = p_user_id AND month_year = current_month;
    ELSE
        -- If no record exists, create a new record with audio_seconds_count equal to p_seconds
        INSERT INTO monthly_user_interactions (user_id, month_year, audio_seconds_count)
        VALUES (p_user_id, current_month, p_seconds);
    END IF;

    -- Return a success message as a JSON object
    RETURN json_build_object('success', true, 'incremented_user_monthly_audio_seconds', p_seconds);
END;
$$;
