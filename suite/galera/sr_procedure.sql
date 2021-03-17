DROP PROCEDURE IF EXISTS sr_procedure;
DELIMITER //
CREATE PROCEDURE sr_procedure (IN row_count int(10), IN fragment_unit varchar(50), IN fragment_size int(10))
BEGIN
    DECLARE trx_statementsVar INT ;
    DECLARE trx_fragmentVar INT ;
    SET trx_statementsVar = 1 ;
    SET trx_fragmentVar = fragment_size * 10 ;
    SET SESSION wsrep_trx_fragment_unit = fragment_unit;
    SET SESSION wsrep_trx_fragment_size = fragment_size;
    SET AUTOCOMMIT=OFF;
    START TRANSACTION;
    IF fragment_unit = 'rows' THEN
        UPDATE sbtest1 set pad = (SELECT LEFT(UUID(), 32)) LIMIT row_count;
    ELSE
        IF fragment_unit = 'statements' THEN
            loop_label: LOOP
                IF trx_statementsVar > fragment_size THEN
                    LEAVE loop_label;
                END IF;
                DELETE FROM sbtest1 LIMIT 1;
                UPDATE sbtest1 set c = (SELECT LEFT(UUID(), 32)) LIMIT 1;
                SET trx_statementsVar = trx_statementsVar + 1;
                ITERATE loop_label;
                END LOOP;
        ELSE
            INSERT INTO sbtest1(k,c,pad) SELECT k,c,pad FROM sbtest1 LIMIT row_count;
        END IF;
    END IF;
    COMMIT;
END //
DELIMITER ;
