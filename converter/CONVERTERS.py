# Converter registry
CONVERTERS = {
    ".rcp.bson": {
            "name": "RCP Files",
            "function": "_convert_rcp_file"
    },
    ".mat":{
            "name": "GIB Mat Files",
            "function": "_convert_mat_file"
    },
    ".rec.bson": {
            "name": "REC Files",
            "function": "_convert_rec_file"
    },
    ".csv": {
            "name": "CSV Sant Joan Files",
            "function": "_convert_csv_file"
    },
}