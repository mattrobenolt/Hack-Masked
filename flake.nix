{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  outputs = { self, nixpkgs }:
    let
      system = "aarch64-darwin";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          (pkgs.python3.withPackages (ps: [
            ps.fonttools
            ps.fontmake
            ps.ufolib2
          ]))
          pkgs.harfbuzz
          pkgs.fontconfig
        ];
      };
    };
}
