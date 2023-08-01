#!/usr/bin/python

import requests
import xmltodict
from pathlib import Path

_excluded_lib_vers = ("dev", "alpha", "beta", "rc")
_destination_dir = "my-lib-repo"
_lib_category = "Android"
_lib_dir = "Google"
_pom_ext = "pom"
_jar_ext = "jar"
_lib_descriptor_name = "library.xml"

def _request_xml(url):
    r = requests.get(url)
    xml = r.text
    dict = xmltodict.parse(xml)
    return dict

def get_artifact_groups():
    artifact_groups_dict = _request_xml("https://maven.google.com/master-index.xml")
    # with open("artifact_groups.xml", "w") as artifact_groups_file:
    #     artifact_groups_file.write(artifact_groups_xml)
    artifact_groups = [x for x in artifact_groups_dict["metadata"]]
    print(">> retrieved from google maven {} artifact groups".format(len(artifact_groups)))
    return artifact_groups

def get_group_libs(artifact_group):
    group_path = artifact_group.replace(".", "/")
    group_libs_dict = _request_xml("https://maven.google.com/{}/group-index.xml".format(group_path))
    group_libs = group_libs_dict[artifact_group]
    print(">>> retrieved metadata for {0} libraries for artifact group '{1}'".format(len(group_libs), artifact_group))
    return group_libs

def curate_lib_vers(lib_vers):
    lib_vers = lib_vers["@versions"]
    cleaned_lib_vers = [x for x in lib_vers.split(',') if not any(x.lower().find(y) != -1 for y in _excluded_lib_vers)]
    return cleaned_lib_vers

def create_lib_dir(artifact_group, lib_name, lib_ver):
    dest_path = Path(_destination_dir, _lib_dir, "{}-{}".format(artifact_group, lib_name), lib_ver)
    if not dest_path.exists():
        dest_path.mkdir(parents=True)
    return dest_path

def _get_lib_file_packaging(artifact_group, lib_name, lib_ver):
    group_path = artifact_group.replace('.', '/')
    pom_url = "https://maven.google.com/{0}/{1}/{2}/{1}-{2}.{3}".format(group_path, lib_name, lib_ver, _pom_ext)
    pom_dict = _request_xml(pom_url)
    val = (pom_dict["project"].get("packaging", _jar_ext), pom_dict["project"].get("name", lib_name))
    return val

def _download_lib_file(artifact_group, lib_name, lib_ver, lib_packaging, lib_path):
    group_path = artifact_group.replace('.', '/')
    lib_url = "https://maven.google.com/{0}/{1}/{2}/{1}-{2}.{3}".format(group_path, lib_name, lib_ver, lib_packaging)
    r = requests.get(lib_url)
    if r.status_code == requests.codes.ok:
        with open(lib_path, "wb") as output:
            output.write(r.content)
        print(">>>>> retrieved library file '{}'".format(lib_path.name))
    else:
        raise Exception("error downloading library file '{}'".format(lib_url))

def _create_lib_descriptor(lib_name, lib_version, lib_category, date, comment, lib_descriptor_path):
    content = "<?xml version=\"1.0\"?>\n" \
              "<library>\n" \
              "    <!-- library name -->\n" \
              "    <name>{0}</name>\n" \
              "\n" \
              "    <!-- Advertising, Analytics, Android, SocialMedia, Cloud, Utilities -->\n" \
              "    <category>{1}</category>\n" \
              "\n" \
              "    <!-- optional: version string -->\n" \
              "    <version>{2}</version>\n" \
              "\n" \
              "    <!-- optional: date (format: dd.MM.yyyy  example: 21.05.2017) -->\n" \
              "    <releasedate>{3}</releasedate>\n" \
              "\n" \
              "    <!-- optional: comment -->\n" \
              "    <comment>{4}</comment>\n" \
              "</library>\n".format(lib_name, lib_category, lib_version, date, comment)
    with open(lib_descriptor_path, "w") as output:
        output.write(content)
    print(">>>>> created descriptor file for library '{}' version {}".format(lib_name, lib_version))


def main():
    # download artifact groups from maven.google.com/master-index.xml
    artifact_groups = get_artifact_groups()
    n1 = len(artifact_groups)
    for i1, artifact_group in enumerate(artifact_groups):
        print(">> processing artifact group {}/{}: {}".format(i1 + 1, n1, artifact_group))
        
        group_libs = get_group_libs(artifact_group)
        # download group library names and versions at maven.google.com/group_path/group-index.xml
        for (lib_name, lib_vers) in group_libs.items():
            lib_vers = curate_lib_vers(lib_vers)

            n2 = len(lib_vers)
            for i2, lib_ver in enumerate(lib_vers):
                print(">>>> processing library {}/{}: '{}-{}' version {}".format(i2 + 1, n2, artifact_group, lib_name, lib_ver))

                # download jar from maven.google.com/group_path/library/version/library-version.ext 
                lib_dir = create_lib_dir(artifact_group, lib_name, lib_ver)
                lib_packaging, lib_fullname = _get_lib_file_packaging(artifact_group, lib_name, lib_ver)
                lib_path = lib_dir.joinpath("{}-{}-{}.{}".format(artifact_group, lib_name, lib_ver, lib_packaging))
                try:
                    if not lib_path.exists():
                        _download_lib_file(artifact_group, lib_name, lib_ver, lib_packaging, lib_path)

                    # create LibScout xml profile
                    lib_descriptor_path = lib_dir.joinpath(_lib_descriptor_name)
                    if not lib_descriptor_path.exists():
                        _create_lib_descriptor(lib_fullname, lib_ver, _lib_category, "", "", lib_descriptor_path)
                except Exception as ex:
                    print(ex)


if __name__ == '__main__':
    main()
else:
    print("loaded as a module")