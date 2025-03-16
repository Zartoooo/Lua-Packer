import argparse
import pathlib
import random
import string
import re

parser = argparse.ArgumentParser()
parser.add_argument("packfile", help="Pack the specified folder in a single file")
parser.add_argument(
    "output",
    help="Specify the file where the packer outputs WILL OVERWRITE IF EXISTING",
)
args = parser.parse_args()


def generate_variable_name(length=8):
    first_char = random.choice(string.ascii_letters)
    remaining_chars = "".join(
        random.choices(string.ascii_letters + string.digits, k=length - 1)
    )
    return first_char + remaining_chars


def _scan_for_requires(source_code):
    return re.findall(r'require\s*\(\s*"([^"]+)"\s*\)', source_code)


def PackProject(ProjDir, OutputFileName):
    project_path = pathlib.Path(ProjDir)
    if not project_path.exists():
        print("Invalid Path For Project")
        return

    ModulesTableName = "Modules_" + generate_variable_name()
    RequireFuncName = "Require_" + generate_variable_name()
    RequiredModulesName = "RequiredModules_" + generate_variable_name()
    FinalFile = f"local {ModulesTableName} = {{}} -- Random name to avoid interfering with original code\n"
    FinalFile += f"local {RequiredModulesName} = {{}} -- Random name to avoid interfering with original code\n"
    FinalFile += f"""local {RequireFuncName} = function(path)
    if {RequiredModulesName}[path] then
        return {RequiredModulesName}[path]
    elseif {ModulesTableName}[path] then
        {RequiredModulesName}[path] = {ModulesTableName}[path]()
        return {RequiredModulesName}[path]
    end

    error("Module '" .. path .. "' not found")
end
"""
    module_content = {}

    for lua_file in project_path.rglob("*.lua"):
        if lua_file.name == "main.lua":
            continue  # Skip main.lua

        with lua_file.open("r", encoding="utf-8") as f:
            content = f.read()
            module_name = str(
                lua_file.relative_to(project_path).with_suffix("")
            ).replace("\\", "/")
            module_content[module_name] = content

    for module_name, content in module_content.items():
        requires = _scan_for_requires(content)
        for req in requires:
            if req in module_content:
                content = re.sub(
                    rf'require\s*\(\s*"{re.escape(req)}"\s*\)',
                    f"{RequireFuncName}('{req}')",
                    content,
                )

        FinalFile += (
            f"{ModulesTableName}['{module_name}'] = function()\n{content}\nend\n"
        )

    main_lua_path = project_path / "main.lua"
    if main_lua_path.exists():
        with main_lua_path.open("r", encoding="utf-8") as f:
            main_content = f.read()
            requires = _scan_for_requires(main_content)
            for req in requires:
                if req in module_content:
                    main_content = re.sub(
                        rf'require\s*\(\s*"{re.escape(req)}"\s*\)',
                        f"{RequireFuncName}('{req}')",
                        main_content,
                    )
            FinalFile += "\n-- Main Lua File --\n"
            FinalFile += main_content

    FinalFile = FinalFile.replace("require", RequireFuncName)
    with open(OutputFileName, "w", encoding="utf-8") as f:
        f.write(FinalFile)

    print(f"Project packed successfully into {OutputFileName}")


PackProject(args.packfile, args.output)