import os


if __name__ == "__main__":
    length = raw_input("Enter encrypt bit length(2048):")
    length = int(length) if length else 2048

    country_code = raw_input("Enter your country code(CN):")
    country_code = country_code if country_code else "CN"
    province = raw_input("Enter your province (NA):")
    province = province if province else "NA"
    location = raw_input("Enter your location (NA):")
    location = location if location else "NA"
    organisation = raw_input("Enter your organisation (NA):")
    organisation = organisation if organisation else "NA"
    organisation_unit_name = raw_input("Enter your organisation unit name (NA):")
    organisation_unit_name = organisation_unit_name if organisation_unit_name else "NA"
    common_name = raw_input("Enter your common_name (NA):")
    common_name = common_name if common_name  else "NA"
    parameters = "/C=%s/ST=%s/L=%s/O=%s/OU=%s/CN=%s" % (
        country_code, province, location, organisation, organisation_unit_name, common_name)
    for cmd in ("openssl genrsa -out ca.key %d" % length,
                "openssl req -new -x509 -days 36500 -key ca.key -out ca.crt -subj %s" % parameters,
                "openssl genrsa -out server.key %d" % length,
                "openssl req -new -key server.key -out server.csr -subj %s" % parameters,
                "mkdir demoCA",
                "mkdir demoCA/newcerts",
                "touch demoCA/index.txt",
                "echo '01' > demoCA/serial",
                "openssl ca -in server.csr -out server.crt -cert ca.crt -keyfile ca.key"):
        print "="*90
        print cmd
        os.popen(cmd)

