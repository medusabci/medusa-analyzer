# Converter registry
CONVERTERS = {
    ".rcp.bson": {
        "converter": "_convert_rcp_file"
    },
    ".mat": {
        "converter": "_convert_mat_file"
    },
    ".rec.bson": {
        "converter": "_convert_rec_file"
    },
    ".csv": {
        "converter": "_convert_csv_file"
    }
}