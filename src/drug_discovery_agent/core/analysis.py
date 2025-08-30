from typing import Dict, Any
import re
from Bio.SeqUtils import molecular_weight
from Bio.SeqUtils.IsoelectricPoint import IsoelectricPoint as IsoelectricPointCalculator
from Bio.Seq import Seq
from drug_discovery_agent.core.uniprot import UniProtClient


class SequenceAnalyzer:
    """Analyzer for protein sequence properties and comparisons."""
    
    def __init__(self, uniprot_client: UniProtClient | None = None):
        """Initialize sequence analyzer with optional UniProt client.
        
        Args:
            uniprot_client: UniProt client instance. If None, creates a new one.
        """
        self.uniprot_client = uniprot_client or UniProtClient()
    
    async def analyze_from_uniprot(self, uniprot_code: str) -> Dict[str, Any]:
        """Analyze properties of a protein sequence for a viral protein.

        Args:
            uniprot_code: The UniProt accession code for the virus protein (e.g., "P0DTC2").

        Returns:
            dict: {
                length: int,
                molecular_weight_kda: float,
                isoelectric_point: float,
                composition: dict
            }
        """
        data = await self.uniprot_client.get_fasta_sequence(uniprot_code)

        lines = data.strip().splitlines()
        if lines and lines[0].startswith(">"):
            lines = lines[1:]
        clean_seq = "".join(lines).upper()

        # Validate amino acids
        if not all(res in "ACDEFGHIKLMNPQRSTVWY" for res in clean_seq):
            return {"error": "Invalid sequence. Only canonical amino acids are supported."}
        
        seq_obj = Seq(clean_seq)
        pI_calc = IsoelectricPointCalculator(str(seq_obj))

        return {
            "length": len(seq_obj),
            "molecular_weight_kda": round(molecular_weight(seq_obj, seq_type='protein') / 1000, 2),
            "isoelectric_point": round(pI_calc.pi(), 2),
            "composition": {aa: clean_seq.count(aa) for aa in sorted(set(clean_seq))}
        }
    
    def analyze_raw_sequence(self, sequence: str) -> Dict[str, Any]:
        """Analyze properties of a raw protein sequence string.
        
        Args:
            sequence: Raw amino acid sequence string.
            
        Returns:
            dict: Analysis results including length, MW, pI, and composition.
        """
        clean_seq = sequence.strip().upper()
        
        # Validate amino acids
        if not all(res in "ACDEFGHIKLMNPQRSTVWY" for res in clean_seq):
            return {"error": "Invalid sequence. Only canonical amino acids are supported."}
        
        seq_obj = Seq(clean_seq)
        pI_calc = IsoelectricPointCalculator(str(seq_obj))

        return {
            "length": len(seq_obj),
            "molecular_weight_kda": round(molecular_weight(seq_obj, seq_type='protein') / 1000, 2),
            "isoelectric_point": round(pI_calc.pi(), 2),
            "composition": {aa: clean_seq.count(aa) for aa in sorted(set(clean_seq))}
        }
    
    async def compare_variant(self, uniprot_id: str, mutation: str) -> Dict[str, Any]:
        """Compare a mutated protein against the reference from UniProt.
        
        Args:
            uniprot_id: UniProt accession (e.g., "P0DTC2").
            mutation: Mutation string in format D614G.

        Returns:
            dict: Differences in molecular weight, charge, and other properties.
        """
        try:
            fasta = await self.uniprot_client.get_fasta_sequence(uniprot_id)
            lines = fasta.strip().splitlines()
            if lines[0].startswith(">"):
                lines = lines[1:]
            wild_seq = "".join(lines).upper()

            match = re.match(r"([A-Z])(\d+)([A-Z])", mutation.strip().upper())
            if not match:
                return {"error": "Invalid mutation format. Use e.g., D614G."}
            orig, pos, new = match.groups()
            pos = int(pos) - 1

            if wild_seq[pos] != orig:
                return {"error": f"Reference mismatch: expected {orig} at position {pos+1}, found {wild_seq[pos]}"}

            mutated_seq = wild_seq[:pos] + new + wild_seq[pos+1:]

            # Analyze both sequences
            wild_props = self.analyze_raw_sequence(wild_seq)
            variant_props = self.analyze_raw_sequence(mutated_seq)

            return {
                "mutation": mutation,
                "wildtype": wild_props,
                "variant": variant_props,
                "position": pos + 1,
                "amino_acid_change": f"{orig} → {new}"
            }

        except Exception as e:
            return {"error": str(e)}