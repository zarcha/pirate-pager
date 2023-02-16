rm -rf build || true
mkdir build

cd manager
rm -rf __pycache__
rm -rf pager.db
rm -rf __MACOSX
rm -rf .DS_Store
zip manager.zip *
mv manager.zip ../build

cd ../node
rm -rf __pycache__
rm -rf pager.db
rm -rf __MACOSX
rm -rf .DS_Store
zip node.zip *
mv node.zip ../build