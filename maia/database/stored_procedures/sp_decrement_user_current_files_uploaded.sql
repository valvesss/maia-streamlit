-- DROP FUNCTION decrement_current_file_uploads(UUID);
CREATE OR REPLACE FUNCTION decrement_user_current_files_uploaded(p_user_id UUID) 
RETURNS JSON LANGUAGE plpgsql AS $$
DECLARE
    new_count SMALLINT;
BEGIN
    -- Get the current count of files uploaded
    SELECT current_files_uploaded INTO new_count
    FROM users
    WHERE id = p_user_id;
    
    -- Only proceed with the decrement if the current count is greater than zero
    IF new_count > 0 THEN
        -- Decrement the current_files_uploaded by 1 for the specified user
        UPDATE users
        SET 
            current_files_uploaded = current_files_uploaded - 1
        WHERE id = p_user_id;
        
        -- Set new_count to the decremented value for the return message
        new_count := new_count - 1;
    END IF;
    
    -- Return a success message as a JSON object, including the updated count
    RETURN json_build_object('success', true, 'decremented_user_current_files_uploaded', 1);
END;
$$;