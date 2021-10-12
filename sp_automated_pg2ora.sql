-- EXEC SP_AUTOMATED_PG2ORA_TRANSFERS(TRANSFER_TYPE => 'PG2ORA', SOURCE_HOST=> '172.31.70.60', TARET_HOST => 'NVAIP01');

CREATE OR REPLACE PROCEDURE SP_AUTOMATED_PG2ORA_TRANSFERS
(transfer_type VARCHAR2, SOURCE_HOST VARCHAR2,TARGET_HOST VARCHAR2)
IS
vquery CLOB;
clientid VARCHAR2(20);
src_schema_name VARCHAR2(200);
dest_schema_name VARCHAR2(200);
src_table_list VARCHAR2(4000);

sessionid INTEGER;
executionid INTEGER;

CURSOR c_table_list IS
    WITH DATA AS
        ( SELECT SOURCE_SCHEMA, REPLACE(REPLACE(SS_TABLELIST,'['),']') AS SRC_TABLE_LIST_IN_PROCESSING FROM odi_wh_build_log
        WHERE JOBTYPE=transfer_type AND SOURCE_HOST=SOURCE_HOST
        AND sswh_execution_status IN ('PROCESSING', 'INITIATE') )
    ,PROCESSING_TABLE AS(
        SELECT DISTINCT(Trim(REGEXP_SUBSTR(SRC_TABLE_LIST_IN_PROCESSING, '[^,]+', 1, LEVEL))) SRC_TABLE_LIST_IN_PROCESSING, SOURCE_SCHEMA
        FROM DATA
        CONNECT BY INSTR(SRC_TABLE_LIST_IN_PROCESSING, ',', 1, LEVEL - 1) > 0 )
    SELECT clientid, src_schema_name,dest_schema_name,
      listagg(src_table_name, ',')within GROUP(ORDER BY clientid,src_schema_name) AS src_table_list
    FROM  pgora_tabletransfer@nvtaxonomy T
    WHERE status='ACTIVE'
    AND NOT EXISTS(
      SELECT SRC_TABLE_LIST_IN_PROCESSING FROM PROCESSING_TABLE P
      WHERE T.SRC_TABLE_NAME = P.SRC_TABLE_LIST_IN_PROCESSING
      AND T.SRC_SCHEMA_NAME = P.SOURCE_SCHEMA)
    GROUP BY clientid, src_schema_name,dest_schema_name;

BEGIN
  OPEN c_table_list;
  LOOP
  FETCH c_table_list INTO clientid, src_schema_name,dest_schema_name,src_table_list;
  EXIT WHEN c_table_list%NOTFOUND;

     -- Get session id
     EXECUTE IMMEDIATE 'select sq_odi_wh_build_log.NEXTVAL from dual' INTO sessionid;
--     Dbms_Output.put_line(sessionid);

    -- Get Execution Id
     EXECUTE IMMEDIATE 'select sq_dsr_odi_wh_executionno.NEXTVAL from dual' INTO executionid;
--     Dbms_Output.put_line(executionid);

     vquery := 'INSERT INTO odi_wh_build_log (WH_SESSION_ID, LEGACYCLIENTID, APPLICATIONID,  CREATED_USER,ODI_SESSION_NAME,
      scen_name,scen_type,jobtype, sswh_execution_status, execution_id,exec_seq,created,
      TARGET_HOST,TARGET_SCHEMA,SOURCE_HOST,SOURCE_SCHEMA ,BATCH_NO, SS_TABLELIST,releasetagidbyapp,processing_reltag)
      VALUES ('||sessionid||', '''||clientid||''', '''||clientid||'-001'', ''Saman Munikar'', '''||transfer_type||'-'||sessionid||''',
       '''||transfer_type||''', '''||transfer_type||''', '''||transfer_type||''', ''INITIATE'','||executionid||', 1, SYSDATE, '''||TARGET_HOST||''',
       '''||dest_schema_name||''','''||SOURCE_HOST||''', '''||src_schema_name||''', ''ALL'', ''['||src_table_list||']'', ''NA'', ''NA'')';
--     Dbms_Output.put_line(vquery);
     EXECUTE IMMEDIATE vquery;

  END LOOP;
  CLOSE c_table_list;
END SP_AUTOMATED_PG2ORA_TRANSFERS;
/