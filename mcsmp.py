from sys import argv
import os
import json
from collections import namedtuple

import requests
requests = requests.Session()
requests.headers.update({'User-Agent':'un-pogaz/MC-Modrinth-Project-Manager/0.4 (un.pogaz@gmail.com)'})

def _json(path, data=None):
    if data is not None:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return data
    
    else:
        try:
            return json.loads(open(path).read())
        except:
            return {}

def root(data=None):
    return _json('mcsmp.json', data)

def _mcsmp(path):
    return os.path.join(path, '.mcsmp.json')
def mcsmp(dir, data=None):
    path = root().get(dir, None)
    
    if not path:
        print(f'The directory "{dir}" his not defined')
        exit()
    
    if not os.path.exists(path):
        print(f'The path "{path}" of the directory "{dir}" doesn\'t exist')
        exit()
    
    edited = False
    data_path = _mcsmp(path)
    if data is not None:
        edited = True
    else:
        if not os.path.exists(data_path):
            data = {}
            edited = True
        else:
            data = _json(data_path)
    
    for k in ['game_version', 'loader']:
        if k not in data:
            data[k] = None
            edited = True
    for k in ['resourcepack', 'mod']:
        if k not in data:
            data[k] = {}
            edited = True
    
    if edited:
        if data and 'path' in data: del data['path']
        _json(data_path, data)
    
    data['path'] = path
    return data


def dir_add(dir, path):
    path = os.path.abspath(path).replace('\\', '/')
    if not os.path.exists(path):
        print(f'The path "{path}" doesn\'t exist')
        exit()
    
    if not os.path.isdir(path):
        print(f'The path "{path}" is not a folder')
        exit()
    
    r = root()
    for k,v in r.items():
        if path == v and dir != k:
            print(f'The path "{path}" is already assosiated to the directory "{k}"')
            exit()
    
    path_old = r.get(dir, None)
    r[dir] = path
    root(r)
    
    if path_old and path_old != path:
        _json(_mcsmp(path), _json(_mcsmp(path_old)))
        os.remove(_mcsmp(path_old))
    
    data = mcsmp(dir)
    
    print(f'Directorie "{dir}" added')
    if not data['game_version'] and not data['loader']:
        print(f"Don't forget to set a 'version' for Minecraft and a 'loader'")
    elif not data['game_version']:
        print(f"Don't forget to set a 'version' for Minecraft")
    elif not data['loader']:
        print(f"Don't forget to set a 'loader'")


def dir_version(dir, version):
    data = mcsmp(dir)
    data['game_version'] = version
    print(f'Directorie "{dir}" set to the version {version}')
    mcsmp(dir, data)

def dir_loader(dir, loader):
    data = mcsmp(dir)
    data['loader'] = loader.lower()
    print(f'Directorie "{dir}" set to the loader {loader}')
    mcsmp(dir, data)


def test_version(dir, data, _exit=True):
    if not data['game_version']:
        print(f'The directory "{dir}" has no defined version')
        if _exit: exit()
        else: return False
    return True

def test_loader(dir, data, _exit=True):
    test_version(dir, data)
    if not data['loader']:
        print(f'The directory "{dir}" has no defined loader')
        if _exit: exit()
        else: return False
    return True


ProjectType = namedtuple('ProjectType', 'folder test')
project_types = {
    'resourcepack':ProjectType('resourcepacks', test_version),
    'mod':ProjectType('mods', test_loader),
}
loaders_alt = {'quilt': ['fabric']}

def test_filename(path_filename):
    enabled = True
    if not os.path.exists(path_filename) and os.path.exists(path_disabled(path_filename)):
        enabled = False
    present = True
    if not os.path.exists(path_filename) and not os.path.exists(path_disabled(path_filename)):
        present = False
        enabled = False
    
    return enabled, present

def project_list(dir):
    
    def print_basic(name, data):
        path = data['path']
        loader = data['loader']
        game_version = data['game_version']
        print(f'"{name}" : {game_version}/{loader} => "{path}"')
    
    if dir is None:
        r = root()
        if not r:
            print(f'No directorys has defined')
            return
        for name in sorted(r):
            print_basic(name, mcsmp(name))
    
    if dir is not None:
        data = mcsmp(dir)
        print_basic(dir, data)
        for type, pt in project_types.items():
            lst = data[type]
            if lst and pt.test(dir, data, False):
                print()
                print(f'--== Installed {pt.folder} ==--')
                for name in sorted(data[type]):
                    enabled, present = test_filename(os.path.join(data['path'], pt.folder, data[type][name]))
                    print(f"{name}" + ('' if enabled else (' [disabled]' if present else ' !!not present!!')))

def project_check(dir, urlslug):
    urlslug = urlslug.lower()
    data = mcsmp(dir)
    test_version(dir, data)
    
    for type, pt in project_types.items():
        if urlslug in data[type]:
            enabled, present = test_filename(os.path.join(data['path'], pt.folder, data[type][urlslug]))
            print(f'"{urlslug}" is installed in the directory "{dir}"'+ ('' if enabled else (' [disabled]' if present else ' !!not present!!')))
            if not present:
                print(f'but the file are not present! Reinstal the project')
            return
    
    print(f'"{urlslug}" is not installed in the directory "{dir}"')


def path_disabled(path):
    return path+'.disabled'
def path_enable(data, type, urlslug, enable):
    urlslug = urlslug.lower()
    path_filename = os.path.join(data['path'], project_types[type].folder, data[type][urlslug])
    
    if enable and os.path.exists(path_disabled(path_filename)):
        os.rename(path_disabled(path_filename), path_filename)
    
    if not enable and os.path.exists(path_filename):
        os.rename(path_filename, path_disabled(path_filename))


def link(wanted):
    return f'https://api.modrinth.com/v2/{wanted}'

def project_install(dir, urlslug):
    data = mcsmp(dir)
    if install_project_file(dir, data, urlslug):
        mcsmp(dir, data)

def project_update(dir):
    data = mcsmp(dir)
    
    total = []
    errors = []
    
    for type, pt in project_types.items():
        if pt.test(dir, data, False):
            for urlslug in data[type]:
                rslt = install_project_file(dir, data, urlslug)
                if rslt is None:
                    errors.append(urlslug)
                if rslt:
                    total.append(urlslug)
                    mcsmp(dir, data)
                print()
    
    print(f'Finaly! {len(total)} projects has been updated in "{dir}"')
    if total:
        print('Updated projects: ' + ', '.join(sorted(total)))
    if errors:
        print(f'but... the following projects have suffered an error during their download:')
        print(', '.join(sorted(errors)))

def install_project_file(dir, data, urlslug):
    urlslug = urlslug.lower()
    urllink = link(f'project/{urlslug}')
    game_version = data['game_version']
    loader = data['loader']
    
    url = requests.get(urllink)
    if not url.ok:
        print(f"Error during url request, the project {urlslug} probably doesn't exist")
        return None
    
    if url.ok:
        project_data = json.loads(url.content)
        project_id = project_data['id']
        project_type = project_data['project_type']
        
        if project_type not in project_types:
            print(f"The project type of {urlslug} is unknow: {project_type}")
            return None
        
        print(f"Fetching versions of {urlslug} for Minecraft '{game_version}' and the loader '{loader}'...")
        
        if project_type == 'resourcepack':
            loader = 'minecraft'
        
        pt = project_types[project_type]
        pt.test(dir, data)
        base_path = os.path.join(data['path'], pt.folder)
        os.makedirs(base_path, exist_ok=True)
        
        all_loaders = [loader]+loaders_alt.get(loader, [])
        params = {'game_versions':f'["{game_version}"]', 'loaders':'["'+'","'.join(all_loaders)+'"]'}
        versions = json.loads(requests.get(f"https://api.modrinth.com/v2/project/{project_id}/version", params=params).content)
        
        version_project = None
        for _loader in all_loaders:
            for v in versions:
                if _loader in v['loaders']:
                    version_project = v['files'][0]
                    break
            if version_project:
                break
        
        if not version_project:
            print(f"No version available")
        
        else:
            filename = version_project['filename']
            filename_old = data[project_type].get(urlslug, None)
            path_filename = os.path.join(base_path, filename)
            
            print(f"Got the link for '{filename}'")
            
            disabled = False
            if os.path.exists(path_disabled(path_filename)):
                disabled = True
                os.rename(path_disabled(path_filename), path_filename)
            
            if filename_old:
                path_filename_old = os.path.join(base_path, filename_old)
                if os.path.exists(path_disabled(path_filename_old)):
                    disabled = True
                    os.rename(path_disabled(path_filename_old), path_filename_old)
                
                if os.path.exists(path_filename_old) and filename_old == filename:
                    print(f'The project {urlslug} is already up to date in "{dir}"')
            
            installed = False
            if not os.path.exists(path_filename) or not filename_old or filename != filename_old:
                print("Downloading project...")
                url = requests.get(version_project['url'])
                if url.ok:
                    with open(path_filename, 'wb') as f:
                        f.write(url.content)
                else:
                    print("Downloading fail!")
                    return None
                
                if filename_old and filename_old != filename:
                    try:
                        os.remove(path_filename_old)
                    except:
                        pass
                    
                data[project_type][urlslug] = filename
                print(f'Done! The project "{urlslug}" has been installed in "{dir}"')
                installed = True
            
            if disabled:
                os.rename(path_filename, path_disabled(path_filename))
            
            return installed
        
        return False


def project_remove(dir, urlslug):
    urlslug = urlslug.lower()
    data = mcsmp(dir)
    test_version(dir, data)
    
    for type, pt in project_types.items():
        if urlslug in data[type]:
            path_filename = os.path.join(data['path'], pt.folder, data[type][urlslug])
            path_enable(data, type, urlslug, True)
            try:
                os.remove(path_filename)
            except:
                pass
            
            del data[type][urlslug]
            mcsmp(dir, data)
            print(f'Project {urlslug} deleted from "{dir}"')
            return
    
    print(f'The project {urlslug} is not installed in "{dir}"')


def project_enable(dir, urlslug, enable):
    urlslug = urlslug.lower()
    data = mcsmp(dir)
    
    for type in project_types:
        if urlslug in data[type]:
            path_enable(data, type, urlslug, enable)
            if enable:
                print(f'Project {urlslug} in "{dir}" is now enabled')
            else:
                print(f'Project {urlslug} in "{dir}" is now disabled')
            return
    
    print(f'The project {urlslug} is not installed in "{dir}"')



def project_info(urlslug):
    urlslug = urlslug.lower()
    urllink = link("project/"+urlslug)
    url = requests.get(urllink)
    if url.ok:
        data = json.loads(url.content)
        data_display = data['title'] + ' ' + data['project_type']
        print('+'+'-'*(len(data_display)+2)+'+')
        print('| ' + data_display + ' |')
        print('+'+'-'*(len(data_display)+2)+'+\n')

        print(data['description'])
        print(
            f"\nThe {data_display} was published on {data['published']}, and was last updated on {data['updated']},\nit has {data['downloads']} downloads and has {data['followers']} followers.")
        print("\nCategories:")
        for i in data['categories']:
            print('    ' + i)
            
        print("\nWays to donate:")
        for i in data['donation_urls']:
            print(f'    {i["platform"]}: {i["url"]}')
        print('\n\n-- DATA  --------------------------------')
        print(f"License: {data['license']['name']}")
        print(f"Serverside: {data['server_side']}")
        print(f"Clientside: {data['client_side']}")
        print('\n\n-- LINKS --------------------------------')
        print(f'Source: {data["source_url"]}')
        print(f'Discord: {data["discord_url"]}')
        print(f'Wiki: {data["wiki_url"]}')
    else:
        print(f"Error during url request, the project {urlslug} probably doesn't exist")


# mcsmp install fabric-18.2 sodium
# mcsmp <CMD> [<DIR> [<PROJECT>]]

def usage():
    print(os.path.basename(argv[0]) + " <CMD> [DIR [PROJECT]]")
    print()
    print("Commands:")
    print("    list [DIR]           - show all installed projects in specified directory (mods, resourcepacks and datapacks)")
    print("                         - if no DIR specified, show all defined directory")
    print("    info <PROJECT>       - show info about a mod")
    print()
    print("    add <DIR> <PATH>         - add a directory, the target path must the root .minecraft folder")
    print("    version <DIR> <ID>       - set Minecraft version of a directory")
    print("    loader <DIR> <ID>        - define the loader of the directory")
    print()
    print("    check <DIR> <PROJECT>       - check if the project is installed")
    print("    install <DIR> <PROJECT>     - install/update a project")
    print("    enable <DIR> <PROJECT>      - enable a project")
    print("    disable <DIR> <PROJECT>     - disable a project")
    print("    remove <DIR> <PROJECT>      - remove a project")
    print("    update <DIR>                - update all projects in a directory")
    print()
    print("DIR is the target directory to manage")
    print("PROJECT is the slug-name of the wanted project")
    exit()


def get_arg_n(idx, required=True):
    if len(argv) <= idx:
        if required:
            usage()
        else:
            return None
    return argv[idx]

def main():
    cmd = get_arg_n(1).lower()
    if False: pass
    
    elif cmd == 'list':
        project_list(get_arg_n(2, False))
    elif cmd == 'info':
        project_info(get_arg_n(2))
        
    elif cmd == 'add':
        dir_add(get_arg_n(2), get_arg_n(3))
    elif cmd == 'version':
        dir_version(get_arg_n(2), get_arg_n(3))
    elif cmd == 'loader':
        dir_loader(get_arg_n(2), get_arg_n(3))
    
    elif cmd == 'check':
        project_check(get_arg_n(2), get_arg_n(3))
    elif cmd == 'install':
        project_install(get_arg_n(2), get_arg_n(3))
    elif cmd == 'enable':
        project_enable(get_arg_n(2), get_arg_n(3), True)
    elif cmd == 'disable':
        project_enable(get_arg_n(2), get_arg_n(3), False)
    elif cmd == 'remove':
        project_remove(get_arg_n(2), get_arg_n(3))
    elif cmd == 'update':
        project_update(get_arg_n(2))
    else:
        usage()

if __name__ == "__main__":
    main()