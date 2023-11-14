-- DROP FUNCTION decrement_user_bytes_usage(UUID, BIGINT);
CREATE OR REPLACE FUNCTION decrement_user_current_file_bytes_storaged(user_id UUID, decrement_value BIGINT) 
RETURNS JSON LANGUAGE plpgsql AS $$
DECLARE
    updated_value BIGINT;
BEGIN
    -- Ensure the decrement value is positive to avoid accidental increments
    IF decrement_value < 0 THEN
        RAISE EXCEPTION 'Decrement value must be positive';
    END IF;

    UPDATE users
    SET current_file_bytes_storaged = current_file_bytes_storaged - decrement_value
    WHERE id = user_id
    RETURNING current_file_bytes_storaged INTO updated_value;

    -- Ensure the updated value is not negative
    IF updated_value < 0 THEN
        -- Optionally, reset the value to 0 if it goes negative
        UPDATE users
        SET current_file_bytes_storaged = 0
        WHERE id = user_id;
        updated_value := 0;
    END IF;

    RETURN json_build_object('success', true, 'decremented_user_current_file_bytes_storaged', updated_value);
END;
$$;
