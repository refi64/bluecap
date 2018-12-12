Name:           bluecap
Version:        0.3
Release:        1%{?dist}
Summary:        A lightweight wrapper over podman for container workflows

License:        MPLv2.0
URL:            https://github.com/kirbyfan64/%{name}
Source0:        https://github.com/kirbyfan64/%{name}/archive/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildRequires: nim >= 0.19.0
Requires:      podman
Requires:      polkit
Requires:      pcre

BuildArch:     %{nim_arches}

%description
A lightweight wrapper over podman that makes it easier to have
container-based workflows.

%prep
%autosetup

%build
nimble config bindir=%{_bindir} datadir=%{_datadir} sysconfdir=%{_sysconfdir}
nimble build

%install
nimble sysinstall %{buildroot}

%files
%license LICENSE
%{_bindir}/%{name}
%{_datadir}/polkit-1/actions/com.refi64.Bluecap.policy
%{_sysconfdir}/bluecap/defaults.json

%changelog
* Tue Dec  4 2018 Ryan Gonzalez <rymg19@gmail.com> - 0.2
- Disable SELinux labeling.
- Mount the entire home partition to make path manipulation easier.
- Make sure to run /etc/profile.d.

* Mon Sep  3 2018 Ryan Gonzalez <rymg19@gmail.com> - 0.1
- First version
