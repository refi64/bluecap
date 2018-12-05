Name:           bluecap
#Version:        0.1
Version:        master
Release:        1%{?dist}
Summary:        A lightweight wrapper over podman for container workflows

License:        MPLv2.0
URL:            https://github.com/kirbyfan64/%{name}
Source0:        https://github.com/kirbyfan64/%{name}/archive/v%{version}.tar.gz#/%{name}-v%{version}.tar.gz

BuildRequires: python3 >= 3.6
Requires:      podman
Requires:      polkit
Requires:      python3 >= 3.6

BuildArch:     noarch

%description
A lightweight wrapper over podman that makes it easier to have
container-based workflows.


%prep
%autosetup

%build
python3 -m compileall %{name}.py
mv __pycache__/%{name}.*.pyc %{name}.pyc

%install

mkdir -p %{buildroot}/%{_bindir}
mkdir -p %{buildroot}/%{_prefix}/lib/%{name}
mkdir -p %{buildroot}/%{_datadir}/polkit-1/actions
mkdir -p %{buildroot}/%{_sysconfdir}/bluecap

cat > %{buildroot}/%{_bindir}/%{name} <<-'EOF'
#!/usr/bin/bash
BLUECAP_REDIRECT_USRBIN=1 /usr/bin/python3 %{_prefix}/lib/%{name}/%{name}.pyc "$@"
EOF

chmod 0755 %{buildroot}/%{_bindir}/%{name}

install -m 0644 %{name}.py* %{buildroot}/%{_prefix}/lib/%{name}/
install -m 0644 data/com.refi64.Bluecap.policy %{buildroot}/%{_datadir}/polkit-1/actions/
install -m 0644 data/defaults.json %{buildroot}/%{_sysconfdir}/bluecap/

%files
%license LICENSE
%dir %{_prefix}/lib/%{name}/
%{_bindir}/%{name}
%{_prefix}/lib/%{name}/%{name}.py*
%{_datadir}/polkit-1/actions/com.refi64.Bluecap.policy
%{_sysconfdir}/bluecap/defaults.json

%changelog
* Mon Sep  3 2018 Ryan Gonzalez <rymg19@gmail.com> - master
- First version
