-- DROP FUNCTION increment_user_current_ai_interactions(UUID);
CREATE OR REPLACE FUNCTION increment_user_current_ai_interactions(
    p_user_id UUID
) RETURNS JSON LANGUAGE plpgsql AS $$
DECLARE
    updated_value INT;
BEGIN
    UPDATE users
    SET current_ai_interactions = current_ai_interactions + 1
    WHERE id = p_user_id
    RETURNING current_ai_interactions INTO updated_value;

    RETURN json_build_object('success', true, 'incremented_user_current_ai_interactions', 1);
END;
$$;