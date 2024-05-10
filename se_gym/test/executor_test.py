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


def test_apply_patch_valid():
    download_dummy_repo()
    se_gym.executor.apply_patch("./temp/dummy", APPLICABLE_PATCH)


def test_apply_patch_invalid():
    download_dummy_repo()
    with pytest.raises(se_gym.executor.MalformedPatchException):
        se_gym.executor.apply_patch("./temp/dummy", UNAPPLICABLE_PATCH)
