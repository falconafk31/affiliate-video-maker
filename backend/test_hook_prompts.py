"""Unit tests for the V3 hook prompt contract; no LLM/network required."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hook_prompts as hp  # noqa: E402


class HookPromptV3Tests(unittest.TestCase):
    def test_registry_has_thirteen_variations(self):
        self.assertEqual(len(hp.HOOK_VARIATIONS_V3), 13)
        self.assertEqual(set(hp.HOOK_VARIATIONS_V3), {
            "viral", "shock", "story", "fomo", "flash", "review", "bundle", "premium",
            "v2_problem", "v2_personal", "v2_education", "v2_contra", "v2_visual",
        })

    def test_platform_validation(self):
        self.assertEqual(hp.get_hook_variation("tiktok", "v2_problem")["key"], "v2_problem")
        self.assertEqual(hp.get_hook_variation("shopee", "v2_visual")["key"], "v2_visual")
        with self.assertRaises(ValueError):
            hp.get_hook_variation("shopee", "viral")
        with self.assertRaises(ValueError):
            hp.get_hook_variation("tiktok", "not-a-style")

    def test_cleaner_normalizes_numbers_labels_and_openers(self):
        cleaned = hp.clean_hook_output(
            "TEKS: Jujur, harga Rp99.000 wow 20% 🔥", "v2_visual"
        )
        self.assertEqual(cleaned, "Harga sembilan puluh sembilan ribu rupiah wow dua puluh persen")

    def test_valid_short_script_passes(self):
        script = (
            "Ruangan panas di meja kerja sering bikin hasil kerja menurun. "
            "Kipas mini ini bisa dipindah ke sudut yang paling kamu butuhkan. "
            "Fungsinya untuk membantu circulasi udara di area meja. "
            "Ukuran kecilnya cocok buat meja yang tidak terlalu luas. "
            "Cek listing produk ini sekarang. Buka keranjang kuning sekarang."
        )
        result = hp.validate_hook_output(
            script, hp.get_hook_variation("tiktok", "viral"), "Kipas mini"
        )
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["word_count"], 47)
        self.assertEqual(result["sentence_count"], 6)

    def test_standard_profile_accepts_63_words_in_10_sentences(self):
        script = (
            "Ruangan panas membuat meja kerja terasa pengap. "
            "Kipas mini ini mudah dipindahkan ke berbagai sudut. "
            "Udara di sekitar meja terasa lebih baik setelah perangkat dinyalakan. "
            "Bentuknya ringkas untuk area kerja yang sempit. "
            "Pengaturan arah udara membantu penyesuaian saat kamu bekerja. "
            "Produk ini cocok digunakan di rumah. "
            "Materialnya ringan dan mudah dipindahkan. "
            "Ruang kerja kecil terbantu. "
            "Cek promo jika tersedia. "
            "Lihat listing produk sekarang."
        )
        result = hp.validate_hook_output(
            script, hp.get_hook_variation("tiktok", "v2_problem"), "Kipas mini"
        )
        self.assertEqual(result["word_count"], 63)
        self.assertEqual(result["sentence_count"], 10)
        self.assertTrue(result["valid"], result["errors"])

    def test_short_output_is_accepted_with_duration_warning(self):
        script = (
            "Ruangan panas membuat meja kerja terasa pengap. "
            "Kipas mini ini mudah dipindahkan. "
            "Buka keranjang kuning dan lihat detail ruang kerja sekarang."
        )
        result = hp.validate_hook_output(
            script, hp.get_hook_variation("tiktok", "viral"), "Kipas mini"
        )
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["duration_ok"])
        self.assertTrue(any("jumlah kata" in warning for warning in result["warnings"]))



    def test_validator_rejects_unsafe_output(self):
        bad = (
            "Stok tinggal dua lusin untuk produk ini sekarang. "
            "Buka keranjang kuning sebelum kehabisan."
        )
        result = hp.validate_hook_output(
            bad, hp.get_hook_variation("shopee", "flash"), "Produk tanpa fakta promo"
        )
        self.assertFalse(result["valid"])
        self.assertIn("sensitif numeric claim absent from input", result["errors"])


if __name__ == "__main__":
    unittest.main()
