-- DROP function increment_user_current_files_uploaded(UUID) 
CREATE OR REPLACE FUNCTION increment_user_current_files_uploaded(p_user_id UUID) 
RETURNS JSON LANGUAGE plpgsql AS $$
BEGIN
    -- Increment the current_files_uploaded by 1 for the specified user
    UPDATE users
    SET 
        current_files_uploaded = current_files_uploaded + 1
    WHERE id = p_user_id;

        -- Return a success message as a JSON object
    RETURN json_build_object('success', true, 'incremented_user_current_files_uploaded', 1);
END;
$$;