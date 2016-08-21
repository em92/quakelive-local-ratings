icon_files_match="icon_(.*)\.png"
for d in */ ; do
  src_path="./$d"
  for f in `ls -1 $src_path`; do
    if [[ $src_path$f =~ $src_path$icon_files_match ]] ; then
      echo $src_path$f
    else
      rm $src_path$f
    fi
  done
done

