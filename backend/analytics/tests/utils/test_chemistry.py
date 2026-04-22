from django.test import TestCase
from analytics.utils.chemistry import _get_generic

class ChemistryUtilsTestCase(TestCase):
    """Tests for drug naming and generic mapping."""

    def test_generic_mapping(self):
        # Known mapping
        self.assertEqual(_get_generic("Paracetamol"), "Acetaminophen")
        self.assertEqual(_get_generic("Aspirin"), "Acetylsalicylic acid")
        
        # Unknown mapping (returns self)
        self.assertEqual(_get_generic("Unknown Drug"), "Unknown Drug")
        
        # Case sensitivity (check behavior)
        # Note: Current implementation is case sensitive
        self.assertEqual(_get_generic("paracetamol"), "paracetamol")
