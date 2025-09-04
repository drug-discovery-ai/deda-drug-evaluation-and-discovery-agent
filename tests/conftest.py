"""Global pytest configuration and fixtures."""

import asyncio
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import respx

from drug_discovery_agent.core.analysis import SequenceAnalyzer
from drug_discovery_agent.core.pdb import PDBClient
from drug_discovery_agent.core.uniprot import UniProtClient
from tests.fixtures.env_helpers import (
    empty_env,
    mock_env_vars,
    openai_api_key,
    openai_model,
)
from tests.fixtures.http_helpers import (
    common_http_errors,
    http_mock_helpers,
)

# Import shared fixtures (avoid duplicating existing ones)
# Import fixtures from other modules
from tests.fixtures.mock_clients import (
    mock_clients,
    mock_pdb_client,
    mock_sequence_analyzer,
    mock_uniprot_client,
)
from tests.fixtures.mock_http_server import (
    CommonApiMocks,
    MockHttpServer,
    async_mock_http_server,
    common_api_mocks,
    mock_external_apis,
    mock_http_server,
    with_mock_http_server,
)
from tests.fixtures.sample_data import (
    invalid_sequence,
    mock_uniprot_details_response,
    mock_uniprot_pdb_response,
    sample_fasta,
    sample_fasta_long,
    sample_sequence,
    spike_protein_pdb_id,
    spike_protein_uniprot_id,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def respx_mock() -> Generator[Any, None, None]:
    """Provide respx mock for testing HTTP requests."""
    with respx.mock as mock:
        yield mock


@pytest.fixture
def sample_uniprot_fasta() -> str:
    """Sample FASTA sequence for testing."""
    return """>sp|P0DTC2|SPIKE_SARS2 Spike glycoprotein OS=Severe acute respiratory syndrome coronavirus 2 OX=2697049 GN=S PE=1 SV=1
MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIHVSGTNGTKRFDNPVLPFNDGVYFASTEKSNIIRGWIFGTTLDSKTQSLLIVNNATNVVIKVCEFQFCNDPFLGVYYHKNNKSWMESEFRVYSSANNCTFEYVSQPFLMDLEGKQGNFKNLREFVFKNIDGYFKIYSKHTPINLVRDLPQGFSALEPLVDLPIGINITRFQTLLALHRSYLTPGDSSSGWTAGAAAYYVGYLQPRTFLLKYNENGTITDAVDCALDPLSETKCTLKSFTVEKGIYQTSNFRVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKCYGVSPTKLNDLCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNNLDSKVGGNYNYLYRLFRKSNLKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTNGVGYQPYRVVVLSFELLHAPATVCGPKKSTNLVKNKCVNFNFNGLTGTGVLTESNKKFLPFQQFGRDIADTTDAVRDPQTLEILDITPCSFGGVSVITPGTNTSNQVAVLYQDVNCTEVPVAIHADQLTPTWRVYSTGSNVFQTRAGCLIGAEHVNNSYECDIPIGAGICASYQTQTNSPRRARSVASQSIIAYTMSLGAENSVAYSNNSIAIPTNFTISVTTEILPVSMTKTSVDCTMYICGDSTECSNLLLQYGSFCTQLNRALTGIAVEQDKNTQEVFAQVKQIYKTPPIKDFGGFNFSQILPDPSKPSKRSFIEDLLFNKVTLADAGFIKQYGDCLGDIAARDLICAQKFNGLTVLPPLLTDEMIAQYTSALLAGTITSGWTFGAGAALQIPFAMQMAYRFNGIGVTQNVLYENQKLIANQFNSAIGKIQDSLSSTASALGKLQDVVNQNAQALNTLVKQLSSNFGAISSVLNDILSRLDKVEAEVQIDRLITGRLQSLQTYVTQQLIRAAEIRASANLAATKMSECVLGQSKRVDFCGKGYHLMSFPQSAPHGVVFLHVTYVPAQEKNFTTAPAICHDGKAHFPREGVFVSNGTHWFVTQRNFYEPQIITTDNTFVSGNCDVVIGIVNNTVYDPLQPELDSFKEELDKYFKNHTSPDVDLGDISGINASVVNIQKEIDRLNEVAKNLNESLIDLQELGKYEQYIKWPWYIWLGFIAGLIAIVMVTIMLCCMTSCCSCLKGCCSCGSCCKFDEDDSEPVLKGVKLHYT"""


@pytest.fixture
def sample_uniprot_details() -> dict[str, Any]:
    """Sample UniProt protein details for testing."""
    return {
        "results": [
            {
                "uniProtKBAccession": "P0DTC2",
                "entryName": "SPIKE_SARS2",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "Spike glycoprotein"}},
                    "alternativeNames": [{"fullName": {"value": "S glycoprotein"}}],
                },
                "organism": {
                    "scientificName": "Severe acute respiratory syndrome coronavirus 2",
                    "commonName": "2019-nCoV",
                    "taxonId": 2697049,
                    "lineage": [
                        "Viruses",
                        "Riboviria",
                        "Orthornavirae",
                        "Pisuviricota",
                        "Pisoniviricetes",
                        "Nidovirales",
                        "Cornidovirineae",
                        "Coronaviridae",
                        "Orthocoronavirinae",
                        "Betacoronavirus",
                        "Sarbecovirus",
                    ],
                },
                "proteinExistence": "1: Evidence at protein level",
                "sequence": {
                    "value": "MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIHVSGTNGTKRFDNPVLPFNDGVYFASTEKSNIIRGWIFGTTLDSKTQSLLIVNNATNVVIKVCEFQFCNDPFLGVYYHKNNKSWMESEFRVYSSANNCTFEYVSQPFLMDLEGKQGNFKNLREFVFKNIDGYFKIYSKHTPINLVRDLPQGFSALEPLVDLPIGINITRFQTLLALHRSYLTPGDSSSGWTAGAAAYYVGYLQPRTFLLKYNENGTITDAVDCALDPLSETKCTLKSFTVEKGIYQTSNFRVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKCYGVSPTKLNDLCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNNLDSKVGGNYNYLYRLFRKSNLKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTNGVGYQPYRVVVLSFELLHAPATVCGPKKSTNLVKNKCVNFNFNGLTGTGVLTESNKKFLPFQQFGRDIADTTDAVRDPQTLEILDITPCSFGGVSVITPGTNTSNQVAVLYQDVNCTEVPVAIHADQLTPTWRVYSTGSNVFQTRAGCLIGAEHVNNSYECDIPIGAGICASYQTQTNSPRRARSVASQSIIAYTMSLGAENSVAYSNNSIAIPTNFTISVTTEILPVSMTKTSVDCTMYICGDSTECSNLLLQYGSFCTQLNRALTGIAVEQDKNTQEVFAQVKQIYKTPPIKDFGGFNFSQILPDPSKPSKRSFIEDLLFNKVTLADAGFIKQYGDCLGDIAARDLICAQKFNGLTVLPPLLTDEMIAQYTSALLAGTITSGWTFGAGAALQIPFAMQMAYRFNGIGVTQNVLYENQKLIANQFNSAIGKIQDSLSSTASALGKLQDVVNQNAQALNTLVKQLSSNFGAISSVLNDILSRLDKVEAEVQIDRLITGRLQSLQTYVTQQLIRAAEIRASANLAATKMSECVLGQSKRVDFCGKGYHLMSFPQSAPHGVVFLHVTYVPAQEKNFTTAPAICHDGKAHFPREGVFVSNGTHWFVTQRNFYEPQIITTDNTFVSGNCDVVIGIVNNTVYDPLQPELDSFKEELDKYFKNHTSPDVDLGDISGINASVVNIQKEIDRLNEVAKNLNESLIDLQELGKYEQYIKWPWYIWLGFIAGLIAIVMVTIMLCCMTSCCSCLKGCCSCGSCCKFDEDDSEPVLKGVKLHYT",
                    "length": 1273,
                    "molWeight": 141178,
                    "crc64": "6A4A02EC81873171",
                },
                "functions": [
                    {
                        "texts": [
                            {
                                "value": "Attaches the virion to the cell membrane by interacting with host receptor"
                            }
                        ]
                    }
                ],
                "uniProtKBCrossReferences": [
                    {
                        "database": "PDB",
                        "id": "6VSB",
                        "properties": [
                            {"key": "Method", "value": "X-ray"},
                            {"key": "Resolution", "value": "3.46 A"},
                        ],
                    },
                    {
                        "database": "PDB",
                        "id": "6VXX",
                        "properties": [
                            {"key": "Method", "value": "X-ray"},
                            {"key": "Resolution", "value": "2.80 A"},
                        ],
                    },
                ],
            }
        ]
    }


@pytest.fixture
def sample_pdb_details() -> dict[str, Any]:
    """Sample PDB structure details for testing."""
    return {
        "data": [
            {
                "rcsb_id": "6VSB",
                "struct": {
                    "title": "Prefusion 2019-nCoV spike glycoprotein with a single receptor-binding domain up",
                    "pdbx_descriptor": "Spike glycoprotein",
                },
                "rcsb_entry_info": {
                    "resolution_combined": [3.46],
                    "structure_determination_methodology": "X-RAY DIFFRACTION",
                    "selected_polymer_entity_types": ["Protein"],
                    "experimental_method": "X-RAY DIFFRACTION",
                },
                "exptl": [{"method": "X-RAY DIFFRACTION"}],
                "rcsb_primary_citation": {
                    "title": "Cryo-EM structure of the 2019-nCoV spike in the prefusion conformation",
                    "journal_abbrev": "Science",
                    "year": 2020,
                },
            }
        ]
    }


@pytest.fixture
def uniprot_client() -> UniProtClient:
    """UniProt client instance."""
    return UniProtClient()


@pytest.fixture
def pdb_client() -> PDBClient:
    """PDB client instance."""
    return PDBClient()


@pytest.fixture
def sequence_analyzer() -> SequenceAnalyzer:
    """Sequence analyzer instance."""
    return SequenceAnalyzer()


@pytest.fixture
def fixtures_path() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_sequences() -> dict[str, str]:
    """Sample protein sequences for testing."""
    return {
        "spike_protein": "MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIHVSGTNGTKRFDNPVLPFNDGVYFASTEKSNIIRGWIFGTTLDSKTQSLLIVNNATNVVIKVCEFQFCNDPFLGVYYHKNNKSWMESEFRVYSSANNCTFEYVSQPFLMDLEGKQGNFKNLREFVFKNIDGYFKIYSKHTPINLVRDLPQGFSALEPLVDLPIGINITRFQTLLALHRSYLTPGDSSSGWTAGAAAYYVGYLQPRTFLLKYNENGTITDAVDCALDPLSETKCTLKSFTVEKGIYQTSNFRVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKCYGVSPTKLNDLCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNNLDSKVGGNYNYLYRLFRKSNLKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTNGVGYQPYRVVVLSFELLHAPATVCGPKKSTNLVKNKCVNFNFNGLTGTGVLTESNKKFLPFQQFGRDIADTTDAVRDPQTLEILDITPCSFGGVSVITPGTNTSNQVAVLYQDVNCTEVPVAIHADQLTPTWRVYSTGSNVFQTRAGCLIGAEHVNNSYECDIPIGAGICASYQTQTNSPRRARSVASQSIIAYTMSLGAENSVAYSNNSIAIPTNFTISVTTEILPVSMTKTSVDCTMYICGDSTECSNLLLQYGSFCTQLNRALTGIAVEQDKNTQEVFAQVKQIYKTPPIKDFGGFNFSQILPDPSKPSKRSFIEDLLFNKVTLADAGFIKQYGDCLGDIAARDLICAQKFNGLTVLPPLLTDEMIAQYTSALLAGTITSGWTFGAGAALQIPFAMQMAYRFNGIGVTQNVLYENQKLIANQFNSAIGKIQDSLSSTASALGKLQDVVNQNAQALNTLVKQLSSNFGAISSVLNDILSRLDKVEAEVQIDRLITGRLQSLQTYVTQQLIRAAEIRASANLAATKMSECVLGQSKRVDFCGKGYHLMSFPQSAPHGVVFLHVTYVPAQEKNFTTAPAICHDGKAHFPREGVFVSNGTHWFVTQRNFYEPQIITTDNTFVSGNCDVVIGIVNNTVYDPLQPELDSFKEELDKYFKNHTSPDVDLGDISGINASVVNIQKEIDRLNEVAKNLNESLIDLQELGKYEQYIKWPWYIWLGFIAGLIAIVMVTIMLCCMTSCCSCLKGCCSCGSCCKFDEDDSEPVLKGVKLHYT",
        "short_protein": "MKTVRQERLKSIVRILERSKEPVSGAQLARKVP",
        "invalid_sequence": "MKTVRQERLXZ",
    }
