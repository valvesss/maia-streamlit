--DROP function increment_user_current_file_bytes_storaged(UUID, BIGINT)
CREATE OR REPLACE FUNCTION increment_user_current_file_bytes_storaged(
    user_id UUID,
    increment_value BIGINT
) RETURNS JSON LANGUAGE plpgsql AS $$
DECLARE
    updated_value BIGINT;
BEGIN
    UPDATE users
    SET current_file_bytes_storaged = current_file_bytes_storaged + increment_value
    WHERE id = user_id
    RETURNING current_file_bytes_storaged INTO updated_value;

    RETURN json_build_object('success', true, 'incremented_user_current_file_bytes_storaged', updated_value);
END;
$$;