"""Constants for API endpoints and configuration."""

# API endpoints
VIRUS_UNIPROT_REST_API_BASE = "https://rest.uniprot.org/uniprotkb"
RCSB_DB_ENDPOINT = "https://data.rcsb.org/rest/v1/core/entry"
EBI_ENDPOINT = "https://www.ebi.ac.uk/ols/api/search"
OPENTARGET_ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"
GENEINFO_ENDPOINT = "https://mygene.info/v3"

# HTTP configuration
USER_AGENT = "FASTA-app/1.0"

# Cache configuration
OPENTARGET_CACHE_DIR = "/tmp/opentarget_cache"
UNIPROT_CACHE_DIR = "/tmp/uniprot_cache"
