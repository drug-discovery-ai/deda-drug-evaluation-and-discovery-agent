"""Shared sample data fixtures for testing."""

import pytest


@pytest.fixture
def sample_fasta():
    """Sample FASTA sequence for testing."""
    return """>sp|P0DTC2|SPIKE_SARS2 Spike glycoprotein
MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIH"""


@pytest.fixture
def sample_sequence():
    """Sample protein sequence for testing."""
    return "MKTVRQERLKSIVRILERSKEPVSGAQLARKIVAPVYKELREASC"


@pytest.fixture
def invalid_sequence():
    """Sample sequence with invalid amino acids for testing."""
    return "MKTVRQERLXZ"


@pytest.fixture
def spike_protein_uniprot_id():
    """SARS-CoV-2 spike protein UniProt ID."""
    return "P0DTC2"


@pytest.fixture
def spike_protein_pdb_id():
    """SARS-CoV-2 spike protein PDB ID."""
    return "6VSB"


# Sample response data constants
MOCK_UNIPROT_DETAILS_RESPONSE = {
    "primaryAccession": "P0DTC2",
    "organism": {
        "scientificName": "Severe acute respiratory syndrome coronavirus 2",
        "lineage": ["Viruses", "Riboviria", "Orthornavirae"],
        "taxonId": 2697049
    },
    "organismHosts": [
        {
            "scientificName": "Homo sapiens",
            "commonName": "Human"
        }
    ],
    "comments": [
        {
            "commentType": "FUNCTION",
            "texts": [
                {
                    "value": "Attaches the virion to the cell membrane"
                }
            ]
        }
    ],
    "proteinDescription": {
        "recommendedName": {
            "fullName": {
                "value": "Spike glycoprotein"
            }
        }
    },
    "sequence": {
        "value": "MFVFLVLLPLVSSQCV"
    }
}

MOCK_UNIPROT_PDB_RESPONSE = {
    "uniProtKBCrossReferences": [
        {
            "database": "PDB",
            "id": "6VSB"
        },
        {
            "database": "PDB",
            "id": "6VXX"
        },
        {
            "database": "EMBL",
            "id": "MT326090"
        },
        {
            "database": "PDB",
            "id": "6VSB"  # Duplicate
        }
    ]
}


@pytest.fixture
def mock_uniprot_details_response():
    """Mock UniProt details response."""
    return MOCK_UNIPROT_DETAILS_RESPONSE.copy()


@pytest.fixture
def mock_uniprot_pdb_response():
    """Mock UniProt PDB response."""
    return MOCK_UNIPROT_PDB_RESPONSE.copy()


@pytest.fixture
def sample_fasta_long():
    """Extended FASTA sequence for testing."""
    return """>sp|P0DTC2|SPIKE_SARS2 Spike glycoprotein
MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIHVSGTNGTKRFDNPVLPFNDGVYFASTEKSNIIRGWIFGTTLDSKTQSLLIVNNATNVVIKVCEFQFCNDPFLGVYYHKNNKSWMESEFRVYSSANNCTFEYVSQPFLMDLEGKQGNFKNLREFVFKNIDGYFKIYSKHTPINLVRDLPQGFSALEPLVDLPIGINITRFQTLLALHRSYLTPGDSSSGWTAGAAAYYVGYLQPRTFLLKYNENGTITDAVDCALDPLSETKCTLKSFTVEKGIYQTSNFRVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKCYGVSPTKLNDLCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNNLDSKVGGNYNYLYRLFRKSNLKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTNGVGYQPYRVVVLSFELLHAPATVCGPKKSTNLVKNKCVNFNFNGLTGTGVLTESNKKFLPFQQFGRDIADTTDAVRDPQTLEILDITPCSFGGVSVITPGTNTSNQVAVLYQDVNCTEVPVAIHADQLTPTWRVYSTGSNVFQTRAGCLIGAEHVNNSYECDIPIGAGICASYQTQTNSPRRARSVASQSIIAYTMSLGAENSVAYSNNSIAIPTNFTISVTTEILPVSMTKTSVDCTMYICGDSTECSNLLLQYGSFCTQLNRALTGIAVEQDKNTQEVFAQVKQIYKTPPIKDFGGFNFSQILPDPSKPSKRSFIEDLLFNKVTLADAGFIKQYGDCLGDIAARDLICAQKFNGLTVLPPLLTDEMIAQYTSALLAGTITSGWTFGAGAALQIPFAMQMAYRFNGIGVTQNVLYENQKLIANQFNSAIGKIQDSLSSTASALGKLQDVVNQNAQALNTLVKQLSSNFGAISSVLNDILSRLDKVEAEVQIDRLITGRLQSLQTYVTQQLIRAAEIRASANLAATKMSECVLGQSKRVDFCGKGYHLMSFPQSAPHGVVFLHVTYVPAQEKNFTTAPAICHDGKAHFPREGVFVSNGTHWFVTQRNFYEPQIITTDNTFVSGNCDVVIGIVNNTVYDPLQPELDSFKEELDKYFKNHTSPDVDLGDISGINASVVNIQKEIDRLNEVAKNLNESLIDLQELGKYEQYIKWPWYIWLGFIAGLIAIVMVTIMLCCMTSCCSCLKGCCSCGSCCKFDEDDSEPVLKGVKLHYT"""