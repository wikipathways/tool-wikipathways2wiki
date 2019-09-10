{ stdenv, python3 }:

let
  inherit (python3.pkgs) buildPythonApplication fetchPypi;
in

buildPythonApplication rec {
  pname = "flask-mwoauth";
  version = "0.4.75";
  name = "${pname}-${version}";

  src = fetchPypi {
    inherit pname version;
    sha256 = "1scvjsl14y8rn5vvah5l4b7fjafm5jma2b8lsihiq9d9ir2f5wkd";
  };

  # TODO get the buildInputs installed in order to run the tests
  doCheck = false;

  propagatedBuildInputs = with python3.pkgs; [
    future
    flask
    mwoauth
    requests
    requests_oauthlib
  ];

  meta = with stdenv.lib; {
    description = "Flask blueprint to run OAuth against MediaWiki's extension:OAuth.";
    homepage = "https://github.com/valhallasw/flask-mwoauth";
    license = licenses.mit;
    maintainers = with maintainers; [ ariutta ];
  };
}
