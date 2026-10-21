import unittest
from compiler import compile_source
class Tests(unittest.TestCase):
 def test_arithmetic(self):
  r=compile_source("let x = 10; let y = 3; print(x * 2 + y);"); self.assertTrue(r["ok"],r["error"]); self.assertEqual(r["output"],"23")
 def test_if(self):
  r=compile_source('let x = 7; if (x > 5) { print("yes"); } else { print("no"); }'); self.assertTrue(r["ok"],r["error"]); self.assertEqual(r["output"],"yes")
 def test_loop(self):
  r=compile_source("let i = 0; while (i < 3) { print(i); i = i + 1; }"); self.assertTrue(r["ok"],r["error"]); self.assertEqual(r["output"],"0\n1\n2")
 def test_undeclared(self):
  r=compile_source("print(missing);"); self.assertFalse(r["ok"]); self.assertIn("used before declaration",r["error"])
 def test_semicolon(self):
  r=compile_source("let x = 4"); self.assertFalse(r["ok"]); self.assertIn("Expected ';'",r["error"])
if __name__=="__main__": unittest.main()
