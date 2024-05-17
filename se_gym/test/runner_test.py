import se_gym
import os
import pytest


def download_dummy_repo():
    """
    Download https://github.com/kyrillschmid/PythonEnv to ./temp/dummy
    """
    if not os.path.exists("./temp"):
        os.makedirs("./temp")
    if not os.path.exists("./temp/dummy"):
        os.system(
            "git clone https://github.com/kyrillschmid/PythonEnv --depth 1  ./temp/dummy"
        )
        open("./temp/dummy/src/python_env/__init__.py", "w").close()


APPLICABLE_PATCH = """\
diff --git a/src/python_env/__main__.py b/src/python_env/__main__.py
index 2b39a9f..652d973 100644
--- a/src/python_env/__main__.py
+++ b/src/python_env/__main__.py
@@ -2,7 +2,8 @@
 
 def main():
     print("hello world")
-    return 2
+    # return 2
+    return 3
 
 
 if __name__ == "__main__":
"""

UNAPPLICABLE_PATCH = """\
diff --git a/file1.txt b/file1.txt
index 0123456..fedcba9 100644
--- a/file1.txt
+++ b/file1.txt
@@ -1 +1,2 @@
 This is the first file.
+This is a random change.
diff --git a/file2.txt b/file2.txt
new file mode 100644
index 0000000..5d308e1
--- /dev/null
+++ b/file2.txt
@@ -0,0 +1 @@
+This is a new file."""

INVALID_TEST_PATH = APPLICABLE_PATCH


def test_apply_patch_valid():
    download_dummy_repo()
    se_gym.apply_patch("./temp/dummy", APPLICABLE_PATCH)


def test_apply_patch_invalid():
    download_dummy_repo()
    with pytest.raises(se_gym.MalformedPatchException):
        se_gym.apply_patch("./temp/dummy", UNAPPLICABLE_PATCH)


def test_apply_patch_and_test_invalid():
    download_dummy_repo()
    tree = se_gym.apply_patch_and_test("./temp/dummy", INVALID_TEST_PATH)
    res = se_gym.runner.parse_pytest_xml(tree)
    assert res["tests.my_test.test_main"]["status"] == "failed"
