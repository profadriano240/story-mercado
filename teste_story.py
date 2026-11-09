import unittest
import datetime as dt
from story import percentual, tem_pregao, titulo


class Testes(unittest.TestCase):
    def test_titulos(self):
        self.assertEqual(titulo(2, 1), "Petróleo e minério sobem antes da abertura")
        self.assertEqual(titulo(-2, -1), "Petróleo e minério caem antes da abertura")
        self.assertEqual(titulo(2, -1), "Petróleo sobe e minério cai antes da abertura")
        self.assertEqual(titulo(0.05, -1), "Petróleo fica estável e minério cai antes da abertura")
        self.assertEqual(titulo(1, 0), "Petróleo sobe e minério fica estável antes da abertura")
        self.assertEqual(titulo(0, 0), "Petróleo e minério estáveis antes da abertura")

    def test_percentual(self):
        self.assertEqual(percentual(2.156), "+2,2%")
        self.assertEqual(percentual(-0.05), "−0,05%")

    def test_pregao(self):
        self.assertTrue(tem_pregao(dt.date(2026, 11, 9)))
        self.assertFalse(tem_pregao(dt.date(2026, 11, 20)))
        self.assertFalse(tem_pregao(dt.date(2026, 11, 14)))


unittest.main()
