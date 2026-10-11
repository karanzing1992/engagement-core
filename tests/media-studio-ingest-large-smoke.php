<?php
/* Real 231 MB streaming upload stress test; peak PHP chunk body about 4MB.
 * No 231MB PHP string, no public webroot storage, no video file in Git.
 */
require __DIR__ . '/media-studio-ingest-smoke.php';
$size = 230924113;
$r = GREC_Media_Ingest::start(req(array(
  'owner_attests_goa_india' => true, 'owner_attests_rights' => true,
  'files' => array(array('name' => 'large-phone.mp4', 'size' => $size)),
)));
check($r instanceof WP_REST_Response && $r->status===201,'231MB stress-test session initialized');
$id = $r->data['id'];
$parts = $r->data['files'][0]['parts'];
$chunk_size = 4194304;
$ctx = hash_init('sha256');
$begin = memory_get_peak_usage(true);
for ($i=0; $i<$parts; $i++) {
    $length = min($chunk_size,$size-$i*$chunk_size);
    $body = str_repeat('K',$length);
    if ($i===0) { $body='0000ftypisom'.substr($body,12); }
    hash_update($ctx,$body);
    $result = GREC_Media_Ingest::chunk(part_request($id,0,$i,$body));
    if (!($result instanceof WP_REST_Response && $result->data['ok'])) {
        throw new Exception("231MB chunk ".$i." failed");
    }
    unset($body);
}
$sha=hash_final($ctx);
$result = GREC_Media_Ingest::finish(req(array('sha256'=>$sha),array('id'=>$id,'file'=>0)));
check($result instanceof WP_REST_Response && $result->data['state']==='ready','Real 231MB segmented transfer assembled successfully');
check($result->data['sha256']===$sha,'Real 231MB final checksum matches');
$path=dirname(ABSPATH).'/.moksha-private-media/'.$id.'/source-0.mp4';
check(filesize($path)===$size,'Full 231MB file exists outside webroot');
check(hash_equals($sha,hash_file('sha256',$path)),'Streamed 231MB bytes verified after assembly');
$peak=memory_get_peak_usage(true);
echo "231MB STRESS TEST SUCCEEDED: ".$parts." chunks, ".number_format($size)." bytes, peak PHP memory ".round($peak/1024/1024,1)." MiB\n";
if ($peak>96*1024*1024) throw new Exception('Unexpected PHP memory use; chunking is not bounded');
