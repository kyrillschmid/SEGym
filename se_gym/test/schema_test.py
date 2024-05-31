import se_gym
import se_gym.output_schema


def test_changepatch():
    schema = se_gym.output_schema.ChangePatchOutput
    schema.code_base_root = "./temp/dummy/"

    cpo = schema(
        filename="src/python_env/__main__.py",
        old_code="""
def main():
    print("hello world")
    return 2
""",
        new_code="""
def main():
    print("hello new world")
    return 3
""",
    )

    assert (
        cpo.patch_file
        == 'diff --git a/src/python_env/__main__.py b/src/python_env/__main__.py\nindex 2b39a9f..26bd973 100644\n--- a/src/python_env/__main__.py\n+++ b/src/python_env/__main__.py\n@@ -1,8 +1,8 @@\n \n \n def main():\n-    print("hello world")\n-    return 2\n+    print("hello new world")\n+    return 3\n \n \n if __name__ == "__main__":\n'
    )
